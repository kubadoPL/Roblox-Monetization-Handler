"""
Serwer MCP (stdio) do zarządzania developer productami i gamepassami Roblox.
Cookie: zmienna ROBLOSECURITY albo cookie.txt obok skryptu.

Rejestracja w Claude Code:
    claude mcp add --scope user roblox-monetization -- python "C:/Users/Jakub/Documents/GitHub/Roblox-DevProduct-Copier/mcp_server.py"

Roblox API nie ma usuwania dev productów ani gamepassów - "usunięcie" = zdjęcie ze sprzedaży (disable_item).
"""

import contextlib
import functools
import io
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from copy_devproducts import KINDS, Roblox, Abort, copy_kind, load_cookie, price_of, bool_str

Kind = Literal["dev", "pass"]

server = MCPServer(
    "roblox-monetization",
    instructions=(
        "Zarządzanie developer productami (kind='dev') i gamepassami (kind='pass') w grach Roblox. "
        "universe_id to universeId gry (z URL-a Creator Dashboard), nie placeId. "
        "Roblox nie pozwala usuwać - disable_item zdejmuje ze sprzedaży. "
        "Przed copy_items z dry_run=False najpierw pokaż użytkownikowi wynik dry_run=True."
    ),
)

_rbx: Roblox | None = None


def rbx() -> Roblox:
    global _rbx
    if _rbx is None:
        _rbx = Roblox(load_cookie(prompt=False))
    return _rbx


def tool(fn):
    # Błędy Roblox API / brak cookie mają dotrzeć do modelu z treścią, a nie jako ogólny crash
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (Abort, RuntimeError, OSError) as e:
            raise ToolError(str(e)) from e
    return server.tool()(wrapper)


def summary(kind: Kind, p: dict) -> dict:
    return {
        "id": p[KINDS[kind]["id_key"]],
        "name": p["name"],
        "price": price_of(p),
        "isForSale": p.get("isForSale"),
        "isManagedPricingEnabled": p.get("isManagedPricingEnabled"),
        "description": p.get("description") or "",
        "iconAssetId": p.get(KINDS[kind]["icon_key"]),
    }


def read_icon(icon_path: str | None) -> bytes | None:
    return Path(icon_path).read_bytes() if icon_path else None


@tool
def list_items(kind: Kind, universe_id: int) -> list[dict]:
    """Lista dev productów ('dev') lub gamepassów ('pass') w grze: id, nazwa, cena, for sale, managed pricing."""
    return [summary(kind, p) for p in rbx().list_items(KINDS[kind], universe_id)]


@tool
def create_item(kind: Kind, universe_id: int, name: str, price: int, description: str = "",
                is_for_sale: bool = True, managed_pricing: bool = False,
                icon_path: str | None = None) -> dict:
    """Tworzy nowy dev product ('dev') lub gamepass ('pass'). icon_path: opcjonalna ścieżka do PNG/JPG."""
    fields = {
        "name": name,
        "description": description,
        "price": str(price),
        "isForSale": bool_str(is_for_sale),
        "isManagedPricingEnabled": bool_str(managed_pricing),
    }
    return summary(kind, rbx().create_item(KINDS[kind], universe_id, fields, read_icon(icon_path)))


@tool
def update_item(kind: Kind, universe_id: int, item_id: int, name: str | None = None,
                description: str | None = None, price: int | None = None,
                is_for_sale: bool | None = None, managed_pricing: bool | None = None,
                icon_path: str | None = None) -> str:
    """Zmienia wybrane pola dev productu / gamepassa. Pola pominięte zostają bez zmian."""
    fields = {}
    if name is not None:
        fields["name"] = name
    if description is not None:
        fields["description"] = description
    if price is not None:
        fields["price"] = str(price)
    if is_for_sale is not None:
        fields["isForSale"] = bool_str(is_for_sale)
    if managed_pricing is not None:
        fields["isManagedPricingEnabled"] = bool_str(managed_pricing)
    if not fields and not icon_path:
        return "Nic do zmiany."
    rbx().update_item(KINDS[kind], universe_id, item_id, fields, read_icon(icon_path))
    return f"Zaktualizowano {item_id}: {', '.join(fields) or 'ikona'}"


@tool
def disable_item(kind: Kind, universe_id: int, item_id: int) -> str:
    """'Usuwa' dev product / gamepass - zdejmuje ze sprzedaży (Roblox API nie ma prawdziwego usuwania)."""
    rbx().update_item(KINDS[kind], universe_id, item_id, {"isForSale": "false"})
    return f"{item_id} zdjęty ze sprzedaży."


@tool
def copy_items(kind: Literal["dev", "pass", "all"], source_universe_id: int, target_universe_id: int,
               dry_run: bool = True, copy_icons: bool = False) -> str:
    """Kopiuje/synchronizuje dev producty i/lub gamepassy ze źródła do celu (po nazwie): tworzy brakujące,
    aktualizuje różniące się cenę/opis/for sale/managed pricing. Zwraca log i mapowanie starych ID na nowe."""
    if source_universe_id == target_universe_id:
        raise Abort("Źródło i cel to ta sama gra.")
    log = io.StringIO()
    # stdout to kanał protokołu MCP - log z copy_kind łapiemy do stringa
    with contextlib.redirect_stdout(log):
        for key in (["dev", "pass"] if kind == "all" else [kind]):
            copy_kind(rbx(), key, source_universe_id, target_universe_id, dry_run, copy_icons,
                      delay=1.0, interactive=False)
    return log.getvalue()


if __name__ == "__main__":
    server.run()
