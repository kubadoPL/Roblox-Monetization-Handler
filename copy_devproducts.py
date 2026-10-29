"""
Kopiuje developer producty z jednej gry Roblox do drugiej (nazwa, opis, cena, for sale,
managed pricing, opcjonalnie ikona). Bez API keya - autoryzacja cookie .ROBLOSECURITY.

Użycie:
    python copy_devproducts.py                      # tryb interaktywny (pyta o wszystko)
    python copy_devproducts.py SOURCE TARGET --dry-run
    python copy_devproducts.py SOURCE TARGET --icons

SOURCE / TARGET to universeId (liczba z URL-a dashboardu: .../experiences/<universeId>/...).
Cookie: zmienna środowiskowa ROBLOSECURITY, plik cookie.txt obok skryptu, albo wklejenie przy starcie.
"""

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path

import requests

API = "https://apis.roblox.com/developer-products/v2/universes"
THUMBS = "https://thumbnails.roblox.com/v1/assets"
HERE = Path(__file__).resolve().parent


class Roblox:
    def __init__(self, cookie: str):
        self.s = requests.Session()
        self.s.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
        self.s.headers["User-Agent"] = "Roblox-DevProduct-Copier"

    def request(self, method: str, url: str, **kw):
        for attempt in range(6):
            r = self.s.request(method, url, timeout=30, **kw)
            token = r.headers.get("x-csrf-token")
            if r.status_code == 403 and token and token != self.s.headers.get("x-csrf-token"):
                self.s.headers["x-csrf-token"] = token
                continue
            if r.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"   rate limit, czekam {wait}s...")
                time.sleep(wait)
                continue
            if r.status_code == 401:
                sys.exit("Błąd 401: cookie nieważne albo wygasło.")
            if not r.ok:
                raise RuntimeError(f"{r.status_code} {r.text[:300]}")
            return r.json() if r.content else None
        raise RuntimeError(f"Za dużo prób: {url}")

    def list_products(self, universe_id: int) -> list[dict]:
        out, token = [], ""
        while True:
            params = {"pageSize": 50}
            if token:
                params["pageToken"] = token
            d = self.request("GET", f"{API}/{universe_id}/developer-products/creator", params=params)
            out.extend(d.get("developerProducts", []))
            token = d.get("nextPageToken")
            if not token:
                return out

    def create_product(self, universe_id: int, fields: dict, icon: bytes | None) -> dict:
        files = {k: (None, v) for k, v in fields.items()}
        if icon:
            files["imageFile"] = ("icon.png", icon, "image/png")
        return self.request("POST", f"{API}/{universe_id}/developer-products", files=files)

    def download_icon(self, asset_id: int) -> bytes | None:
        if not asset_id:
            return None
        d = self.request("GET", THUMBS, params={"assetIds": asset_id, "size": "420x420", "format": "Png"})
        url = (d.get("data") or [{}])[0].get("imageUrl")
        if not url:
            return None
        r = self.s.get(url, timeout=30)
        return r.content if r.ok else None


def price_of(p: dict) -> int | None:
    info = p.get("priceInformation") or {}
    price = info.get("defaultPriceInRobux")
    return int(price) if price is not None else None


def load_cookie() -> str:
    cookie = os.environ.get("ROBLOSECURITY", "").strip()
    if not cookie and (HERE / "cookie.txt").exists():
        cookie = (HERE / "cookie.txt").read_text(encoding="utf-8").strip()
    if not cookie:
        print("Wklej cookie .ROBLOSECURITY (F12 -> Application -> Cookies -> roblox.com).")
        print("Nie będzie widoczne podczas wklejania.")
        cookie = getpass.getpass("Cookie: ").strip()
    if not cookie:
        sys.exit("Brak cookie.")
    return cookie


def ask_int(prompt: str) -> int:
    while True:
        v = input(prompt).strip()
        if v.isdigit():
            return int(v)
        print("Podaj samą liczbę.")


def main():
    ap = argparse.ArgumentParser(description="Kopiowanie developer productów między grami Roblox.")
    ap.add_argument("source", nargs="?", type=int, help="universeId gry źródłowej")
    ap.add_argument("target", nargs="?", type=int, help="universeId gry docelowej")
    ap.add_argument("--dry-run", action="store_true", help="tylko podgląd, nic nie tworzy")
    ap.add_argument("--icons", action="store_true", help="kopiuj też ikony")
    ap.add_argument("--delay", type=float, default=1.5, help="przerwa między produktami (s)")
    args = ap.parse_args()

    interactive = args.source is None or args.target is None
    source = args.source or ask_int("universeId gry ŹRÓDŁOWEJ: ")
    target = args.target or ask_int("universeId gry DOCELOWEJ: ")
    if source == target:
        sys.exit("Źródło i cel to ta sama gra.")

    rbx = Roblox(load_cookie())

    print(f"\nPobieram produkty z {source}...")
    src = rbx.list_products(source)
    print(f"Pobieram produkty z {target}...")
    existing = {p["name"]: p["productId"] for p in rbx.list_products(target)}

    to_create = [p for p in src if p["name"] not in existing]
    print(f"\nŹródło: {len(src)} | już w celu: {len(src) - len(to_create)} | do utworzenia: {len(to_create)}\n")

    no_price = [p for p in to_create if price_of(p) is None and p.get("isForSale")]
    for p in src:
        status = "pomijam (istnieje)" if p["name"] in existing else "NOWY"
        print(f"  {price_of(p)!s:>6} R$  {p['name']}  [{status}]")

    if no_price:
        print("\nUWAGA: nie udało się odczytać ceny dla części produktów. Surowe dane pierwszego:")
        print(json.dumps(no_price[0], indent=2, ensure_ascii=False))
        sys.exit("Przerwano - pokaż te dane, żeby poprawić price_of().")

    if args.dry_run or not to_create:
        print("\nDry run - nic nie utworzono." if args.dry_run else "\nNic do zrobienia.")
        mapping = {p["productId"]: existing[p["name"]] for p in src if p["name"] in existing}
    else:
        if interactive and input(f"\nUtworzyć {len(to_create)} produktów w {target}? [t/N]: ").strip().lower() != "t":
            sys.exit("Anulowano.")
        icons = args.icons or (interactive and input("Kopiować ikony? [t/N]: ").strip().lower() == "t")

        mapping = {p["productId"]: existing[p["name"]] for p in src if p["name"] in existing}
        failed = []
        for i, p in enumerate(to_create, 1):
            fields = {
                "name": p["name"],
                "description": p.get("description") or "",
                "isForSale": str(bool(p.get("isForSale"))).lower(),
                "isManagedPricingEnabled": str(bool(p.get("isManagedPricingEnabled"))).lower(),
            }
            price = price_of(p)
            if price is not None:
                fields["price"] = str(price)

            icon = None
            if icons:
                try:
                    icon = rbx.download_icon(p.get("iconImageAssetId"))
                except Exception as e:
                    print(f"   ikona nie poszła: {e}")

            try:
                new = rbx.create_product(target, fields, icon)
                mapping[p["productId"]] = new["productId"]
                print(f"[{i}/{len(to_create)}] OK  {p['name']}  {p['productId']} -> {new['productId']}")
            except Exception as e:
                failed.append(p["name"])
                print(f"[{i}/{len(to_create)}] BŁĄD  {p['name']}: {e}")
            time.sleep(args.delay)

        if failed:
            print(f"\nNie udało się: {len(failed)} - odpal ponownie, istniejące zostaną pominięte.")

    # Mapowanie stare ID -> nowe ID do podmiany w kodzie gry
    names = {p["productId"]: p["name"] for p in src}
    out_json = HERE / f"mapping_{source}_to_{target}.json"
    out_lua = HERE / f"mapping_{source}_to_{target}.lua"
    out_json.write_text(json.dumps({str(k): v for k, v in mapping.items()}, indent=2), encoding="utf-8")
    lua = "return {\n" + "".join(f"\t[{old}] = {new}, -- {names[old]}\n" for old, new in mapping.items()) + "}\n"
    out_lua.write_text(lua, encoding="utf-8")
    print(f"\nMapowanie zapisane: {out_json.name}, {out_lua.name}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPrzerwano.")
    finally:
        if len(sys.argv) == 1:
            input("\nEnter, żeby zamknąć...")
