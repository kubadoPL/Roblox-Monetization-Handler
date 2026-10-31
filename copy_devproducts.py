"""
Roblox Monetization Handler - copies / syncs developer products and game passes between Roblox experiences
(name, description, price, for sale, managed pricing, optionally the icon).
Items that already exist in the target (matched by name) are updated when anything differs.
No API key - authenticates with the .ROBLOSECURITY cookie.

Usage:
    python copy_devproducts.py                                  # interactive menu
    python copy_devproducts.py copy dev  SOURCE TARGET --dry-run
    python copy_devproducts.py copy pass SOURCE TARGET --icons
    python copy_devproducts.py copy all  SOURCE TARGET
    python copy_devproducts.py list all  UNIVERSE
    python copy_devproducts.py upload FOLDER_OR_FILES... [--group GROUP_ID]
    python copy_devproducts.py lang pl                          # en / pl, saved to settings.json

SOURCE / TARGET / UNIVERSE are universe IDs (from the dashboard URL: .../experiences/<universeId>/...).
Cookie: ROBLOSECURITY env variable, cookie.txt next to the script, or pasted at startup.
"""

import argparse
import getpass
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

import i18n
from i18n import t, is_yes

HERE = Path(__file__).resolve().parent
THUMBS = "https://thumbnails.roblox.com/v1/assets"
ASSETS = "https://apis.roblox.com/assets/user-auth/v1"
ASSET_DELIVERY = "https://assetdelivery.roblox.com/v1/asset/"
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".bmp": "image/bmp",
               ".tga": "image/tga"}

KINDS = {
    "dev": {
        "label": "kind_dev",
        "slug": "devproducts",
        "base": "https://apis.roblox.com/developer-products/v2/universes/{u}/developer-products",
        "list_key": "developerProducts",
        "id_key": "productId",
        "icon_key": "iconImageAssetId",
    },
    "pass": {
        "label": "kind_pass",
        "slug": "gamepasses",
        "base": "https://apis.roblox.com/game-passes/v1/universes/{u}/game-passes",
        "list_key": "gamePasses",
        "id_key": "gamePassId",
        "icon_key": "iconAssetId",
    },
}


class Abort(Exception):
    pass


class Roblox:
    def __init__(self, cookie: str):
        self.s = requests.Session()
        self.s.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
        self.s.headers["User-Agent"] = "Roblox-Monetization-Handler"

    def request(self, method: str, url: str, **kw):
        for attempt in range(6):
            r = self.s.request(method, url, timeout=30, **kw)
            token = r.headers.get("x-csrf-token")
            if r.status_code == 403 and token and token != self.s.headers.get("x-csrf-token"):
                self.s.headers["x-csrf-token"] = token
                continue
            if r.status_code == 429:
                wait = 5 * (attempt + 1)
                print(t("rate_limit", wait=wait))
                time.sleep(wait)
                continue
            if r.status_code == 401:
                raise Abort(t("err_401"))
            if not r.ok:
                raise RuntimeError(f"{r.status_code} {r.text[:300]}")
            return r.json() if r.content else None
        raise RuntimeError(t("too_many_retries", url=url))

    def list_items(self, kind: dict, universe_id: int) -> list[dict]:
        out, token = [], ""
        while True:
            params = {"pageSize": 50}
            if token:
                params["pageToken"] = token
            d = self.request("GET", kind["base"].format(u=universe_id) + "/creator", params=params)
            out.extend(d.get(kind["list_key"]) or [])
            token = d.get("nextPageToken")
            if not token:
                return out

    def create_item(self, kind: dict, universe_id: int, fields: dict, icon: bytes | None) -> dict:
        files = {k: (None, v) for k, v in fields.items()}
        if icon:
            files["imageFile"] = ("icon.png", icon, "image/png")
        return self.request("POST", kind["base"].format(u=universe_id), files=files)

    def update_item(self, kind: dict, universe_id: int, item_id: int, fields: dict, icon: bytes | None = None) -> None:
        files = {k: (None, v) for k, v in fields.items()}
        if icon:
            files["imageFile"] = ("icon.png", icon, "image/png")
        self.request("PATCH", kind["base"].format(u=universe_id) + f"/{item_id}", files=files)

    def user_id(self) -> int:
        if not getattr(self, "_user_id", None):
            self._user_id = self.request("GET", "https://users.roblox.com/v1/users/authenticated")["id"]
        return self._user_id

    def upload_image(self, path: Path, name: str | None = None, description: str = "",
                     group_id: int | None = None) -> dict:
        """Uploads an image as a Decal. Returns the decal id and the id of its image - the one
        ImageLabel.Image / renderImage need (rbxassetid://<image>)."""
        creator = {"groupId": str(group_id)} if group_id else {"userId": str(self.user_id())}
        request = {
            "assetType": "Decal",
            "displayName": (name or path.stem)[:50],
            "description": description,
            "creationContext": {"creator": creator},
        }
        content_type = IMAGE_TYPES.get(path.suffix.lower(), "image/png")
        files = {
            "request": (None, json.dumps(request), "application/json"),
            "fileContent": (path.name, path.read_bytes(), content_type),
        }
        op = self.request("POST", f"{ASSETS}/assets", files=files)
        op_id = op.get("operationId") or op.get("path", "").split("/")[-1]
        for _ in range(30):
            if op.get("done"):
                break
            time.sleep(2)
            op = self.request("GET", f"{ASSETS}/operations/{op_id}")
        if not op.get("done"):
            raise RuntimeError(t("up_timeout"))
        decal_id = int(op["response"]["assetId"])

        # The decal's XML names its image
        image_id = None
        for _ in range(10):
            r = self.s.get(ASSET_DELIVERY, params={"id": decal_id}, timeout=30)
            match = r.ok and re.search(r"id=(\d+)", r.text)
            if match:
                image_id = int(match.group(1))
                break
            time.sleep(3)
        return {"name": path.stem, "decalId": decal_id, "imageId": image_id}

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


def bool_str(v) -> str:
    return str(bool(v)).lower()


def diff_fields(src: dict, dst: dict) -> dict:
    """Fields to PATCH so that dst matches src."""
    fields = {}
    if (src.get("description") or "") != (dst.get("description") or ""):
        fields["description"] = src.get("description") or ""
    if bool(src.get("isForSale")) != bool(dst.get("isForSale")):
        fields["isForSale"] = bool_str(src.get("isForSale"))
    sp = price_of(src)
    if sp is not None and sp != price_of(dst):
        fields["price"] = str(sp)
    if bool(src.get("isManagedPricingEnabled")) != bool(dst.get("isManagedPricingEnabled")):
        fields["isManagedPricingEnabled"] = bool_str(src.get("isManagedPricingEnabled"))
    return fields


def describe_diff(src: dict, dst: dict, fields: dict) -> str:
    parts = []
    if "price" in fields:
        parts.append(t("d_price", old=price_of(dst), new=fields["price"]))
    if "isForSale" in fields:
        parts.append(t("d_sale", v=fields["isForSale"]))
    if "isManagedPricingEnabled" in fields:
        parts.append(t("d_managed", v=fields["isManagedPricingEnabled"]))
    if "description" in fields:
        parts.append(t("d_desc"))
    return ", ".join(parts)


def copy_kind(rbx: Roblox, key: str, source: int, target: int, dry_run: bool, icons: bool | None,
              delay: float, interactive: bool):
    kind = KINDS[key]
    id_key = kind["id_key"]
    print(f"\n===== {t(kind['label'])} =====")
    print(t("fetching", id=source))
    src = rbx.list_items(kind, source)
    print(t("fetching", id=target))
    existing = {p["name"]: p for p in rbx.list_items(kind, target)}

    to_create, to_update = [], []
    for p in src:
        dst = existing.get(p["name"])
        if dst is None:
            to_create.append(p)
            status = t("st_new")
        else:
            fields = diff_fields(p, dst)
            if fields:
                to_update.append((p, dst, fields))
                status = t("st_change", diff=describe_diff(p, dst, fields))
            else:
                status = t("st_same")
        print(f"  {price_of(p)!s:>6} R$  {p['name']}  [{status}]")

    print("\n" + t("summary", src=len(src), new=len(to_create), upd=len(to_update),
                   same=len(src) - len(to_create) - len(to_update)))

    no_price = [p for p in to_create + [u[0] for u in to_update] if price_of(p) is None and p.get("isForSale")]
    if no_price:
        print("\n" + t("no_price"))
        print(json.dumps(no_price[0], indent=2, ensure_ascii=False))
        raise Abort(t("no_price_abort"))

    mapping = {p[id_key]: existing[p["name"]][id_key] for p in src if p["name"] in existing}

    if dry_run or not (to_create or to_update):
        print(t("dry_run") if dry_run else t("nothing"))
    elif interactive and not is_yes(input("\n" + t("confirm", new=len(to_create), upd=len(to_update)))):
        print(t("skipped"))
    else:
        if icons is None:
            icons = bool(to_create) and is_yes(input(t("ask_icons")))
        managed_allowed = True
        failed = []

        def send(action, fields):
            # The target experience may not have accepted Managed Pricing - then send without it
            nonlocal managed_allowed
            if not managed_allowed:
                fields.pop("isManagedPricingEnabled", None)
            try:
                return action(fields)
            except RuntimeError as e:
                if "InvalidManagedPricing" not in str(e):
                    raise
                if managed_allowed:
                    managed_allowed = False
                    print(t("managed_off"))
                fields.pop("isManagedPricingEnabled", None)
                return action(fields) if fields else None

        total = len(to_create) + len(to_update)
        n = 0
        for p in to_create:
            n += 1
            fields = {
                "name": p["name"],
                "description": p.get("description") or "",
                "isForSale": bool_str(p.get("isForSale")),
                "isManagedPricingEnabled": bool_str(p.get("isManagedPricingEnabled")),
            }
            if price_of(p) is not None:
                fields["price"] = str(price_of(p))
            icon = None
            if icons:
                try:
                    icon = rbx.download_icon(p.get(kind["icon_key"]))
                except Exception as e:
                    print(t("icon_failed", err=e))
            try:
                new = send(lambda f: rbx.create_item(kind, target, f, icon), fields)
                mapping[p[id_key]] = new[id_key]
                print(t("p_new", n=n, total=total, name=p["name"], old=p[id_key], new=new[id_key]))
            except Exception as e:
                failed.append(p["name"])
                print(t("p_error", n=n, total=total, name=p["name"], err=e))
            time.sleep(delay)

        for p, dst, fields in to_update:
            n += 1
            try:
                send(lambda f: rbx.update_item(kind, target, dst[id_key], f), fields)
                print(t("p_change", n=n, total=total, name=p["name"]))
            except Exception as e:
                failed.append(p["name"])
                print(t("p_error", n=n, total=total, name=p["name"], err=e))
            time.sleep(delay)

        if failed:
            print("\n" + t("failed", count=len(failed)))
        if not managed_allowed:
            print("\n" + t("managed_hint"))

    # Old ID -> new ID mapping, for replacing IDs in game scripts
    names = {p[id_key]: p["name"] for p in src}
    stem = f"mapping_{kind['slug']}_{source}_to_{target}"
    (HERE / f"{stem}.json").write_text(json.dumps({str(k): v for k, v in mapping.items()}, indent=2),
                                       encoding="utf-8")
    lua = "return {\n" + "".join(f"\t[{old}] = {new}, -- {names[old]}\n" for old, new in mapping.items()) + "}\n"
    (HERE / f"{stem}.lua").write_text(lua, encoding="utf-8")
    print(t("mapping_saved", stem=stem))


def list_kind(rbx: Roblox, key: str, universe: int):
    kind = KINDS[key]
    items = rbx.list_items(kind, universe)
    print(f"\n===== {t(kind['label'])} ({len(items)}) =====")
    for p in items:
        print(f"{p[kind['id_key']]}\t{price_of(p)!s:>6} R$\t{p['name']}")

    out_dir = HERE / "lists"
    out_dir.mkdir(exist_ok=True)
    stem = f"list_{kind['slug']}_{universe}"
    txt = "".join(f"{p[kind['id_key']]}\t{price_of(p)}\t{p['name']}\n" for p in items)
    (out_dir / f"{stem}.txt").write_text(txt, encoding="utf-8")
    lua = "return {\n" + "".join(
        f"\t[{json.dumps(p['name'], ensure_ascii=False)}] = {p[kind['id_key']]},\n" for p in items) + "}\n"
    (out_dir / f"{stem}.lua").write_text(lua, encoding="utf-8")
    print(t("saved", stem=f"lists/{stem}"))


def load_cookie(prompt: bool = True) -> str:
    cookie = os.environ.get("ROBLOSECURITY", "").strip()
    if not cookie and (HERE / "cookie.txt").exists():
        cookie = (HERE / "cookie.txt").read_text(encoding="utf-8").strip()
    if not cookie and not prompt:
        raise Abort(t("no_cookie_mcp"))
    if not cookie:
        print(t("paste_cookie"))
        print(t("hidden"))
        cookie = getpass.getpass("Cookie: ").strip()
    if not cookie:
        sys.exit(t("no_cookie"))
    return cookie


def image_files(paths: list[str]) -> list[Path]:
    """Every image among the given files and folders (folders: their images, not subfolders)."""
    files = []
    for raw in paths:
        p = Path(raw.strip().strip('"'))
        if p.is_dir():
            files.extend(sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_TYPES))
        elif p.is_file() and p.suffix.lower() in IMAGE_TYPES:
            files.append(p)
    return files


def upload_images(rbx: Roblox, paths: list[str], group_id: int | None = None) -> list[dict]:
    """Uploads the images, prints name -> image id and saves the mapping to lists/."""
    files = image_files(paths)
    if not files:
        raise Abort(t("up_none"))
    results = []
    for n, path in enumerate(files, 1):
        try:
            res = rbx.upload_image(path, group_id=group_id)
            print(t("up_ok", n=n, total=len(files), name=res["name"], image=res["imageId"], decal=res["decalId"]))
            results.append(res)
        except (RuntimeError, OSError) as e:
            print(t("up_error", n=n, total=len(files), name=path.stem, err=e))
            results.append({"name": path.stem, "error": str(e)})

    out_dir = HERE / "lists"
    out_dir.mkdir(exist_ok=True)
    stem = f"images_{time.strftime('%Y%m%d_%H%M%S')}"
    (out_dir / f"{stem}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lua = "return {\n" + "".join(
        f'\t[{json.dumps(r["name"])}] = "rbxassetid://{r["imageId"]}",\n' for r in results if r.get("imageId")
    ) + "}\n"
    (out_dir / f"{stem}.lua").write_text(lua, encoding="utf-8")
    print(t("saved", stem=f"lists/{stem}"))
    return results


def ask_int(prompt: str) -> int:
    while True:
        v = input(prompt).strip()
        if v.isdigit():
            return int(v)
        print(t("number_only"))


def kinds_for(choice: str) -> list[str]:
    return ["dev", "pass"] if choice == "all" else [choice]


def toggle_language():
    codes = list(i18n.LANGUAGES)
    code = codes[(codes.index(i18n.lang) + 1) % len(codes)]
    i18n.set_language(code)
    print(t("lang_set", lang=i18n.LANGUAGES[code]))


def menu():
    actions = {
        "1": ("copy", "dev"),
        "2": ("copy", "pass"),
        "3": ("copy", "all"),
        "4": ("list", "all"),
    }
    rbx = None
    while True:
        print()
        for key in ("m_copy_dev", "m_copy_pass", "m_copy_all", "m_list", "m_upload"):
            print(t(key))
        print(t("m_lang", lang=i18n.LANGUAGES[i18n.lang]))
        print(t("m_exit"))
        choice = input("> ").strip()
        if choice == "0":
            return
        if choice == "9":
            toggle_language()
            continue
        if choice not in actions and choice != "5":
            continue
        # Ask for the cookie only on the first action, so the language can be changed without signing in
        rbx = rbx or Roblox(load_cookie())
        if choice == "5":
            try:
                upload_images(rbx, [input(t("ask_upload_path"))])
            except (Abort, RuntimeError) as e:
                print(f"\n{e}")
            continue
        cmd, what = actions[choice]
        try:
            if cmd == "copy":
                source = ask_int(t("ask_source"))
                target = ask_int(t("ask_target"))
                if source == target:
                    raise Abort(t("same_game"))
                for key in kinds_for(what):
                    copy_kind(rbx, key, source, target, dry_run=False, icons=None, delay=1.0, interactive=True)
            else:
                universe = ask_int(t("ask_universe"))
                for key in kinds_for(what):
                    list_kind(rbx, key, universe)
        except (Abort, RuntimeError) as e:
            print(f"\n{e}")


def main():
    if len(sys.argv) == 1:
        menu()
        return

    ap = argparse.ArgumentParser(description=t("cli_desc"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("copy", help=t("cli_copy"))
    c.add_argument("what", choices=["dev", "pass", "all"])
    c.add_argument("source", type=int, help=t("cli_source"))
    c.add_argument("target", type=int, help=t("cli_target"))
    c.add_argument("--dry-run", action="store_true", help=t("cli_dry"))
    c.add_argument("--icons", action="store_true", help=t("cli_icons"))
    c.add_argument("--delay", type=float, default=1.0, help=t("cli_delay"))

    l = sub.add_parser("list", help=t("cli_list"))
    l.add_argument("what", choices=["dev", "pass", "all"])
    l.add_argument("universe", type=int)

    u = sub.add_parser("upload", help=t("cli_upload"))
    u.add_argument("paths", nargs="+", help=t("cli_upload_paths"))
    u.add_argument("--group", type=int, default=None, help=t("cli_group"))

    g = sub.add_parser("lang", help=t("cli_lang"))
    g.add_argument("code", choices=list(i18n.LANGUAGES))

    args = ap.parse_args()
    if args.cmd == "lang":
        i18n.set_language(args.code)
        print(t("lang_set", lang=i18n.LANGUAGES[args.code]))
        return

    rbx = Roblox(load_cookie())
    try:
        if args.cmd == "copy":
            if args.source == args.target:
                raise Abort(t("same_game"))
            for key in kinds_for(args.what):
                copy_kind(rbx, key, args.source, args.target, args.dry_run, args.icons, args.delay,
                          interactive=False)
        elif args.cmd == "upload":
            upload_images(rbx, args.paths, args.group)
        else:
            for key in kinds_for(args.what):
                list_kind(rbx, key, args.universe)
    except Abort as e:
        sys.exit(str(e))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + t("interrupted"))
    finally:
        if len(sys.argv) == 1:
            input("\n" + t("press_enter"))
