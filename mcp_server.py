"""
MCP server (stdio) for managing Roblox developer products and game passes.
Cookie: ROBLOSECURITY env variable or cookie.txt next to the script.

Register in Claude Code:
    claude mcp add --scope user roblox-monetization -- python "C:/path/to/mcp_server.py"

The Roblox API can't delete developer products or game passes - disable_item takes them off sale instead.
"""

import contextlib
import functools
import io
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from copy_devproducts import KINDS, Roblox, Abort, copy_kind, load_cookie, price_of, bool_str
from i18n import t

Kind = Literal["dev", "pass"]

server = MCPServer(
    "roblox-monetization",
    instructions=(
        "Manages Roblox developer products (kind='dev') and game passes (kind='pass'). "
        "universe_id is the experience's universe ID (from the Creator Dashboard URL), not the place ID. "
        "Roblox doesn't allow deleting - disable_item takes an item off sale. "
        "Before calling copy_items with dry_run=False, show the user the dry_run=True result first."
    ),
)

_rbx: Roblox | None = None


def rbx() -> Roblox:
    global _rbx
    if _rbx is None:
        _rbx = Roblox(load_cookie(prompt=False))
    return _rbx


def tool(fn):
    # Roblox API errors / missing cookie should reach the model with their message, not as a generic crash
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
    """Lists developer products ('dev') or game passes ('pass') in an experience: id, name, price, for sale,
    managed pricing."""
    return [summary(kind, p) for p in rbx().list_items(KINDS[kind], universe_id)]


@tool
def create_item(kind: Kind, universe_id: int, name: str, price: int, description: str = "",
                is_for_sale: bool = True, managed_pricing: bool = False,
                icon_path: str | None = None) -> dict:
    """Creates a developer product ('dev') or game pass ('pass'). icon_path: optional local PNG/JPG file."""
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
    """Changes selected fields of a developer product / game pass. Omitted fields stay unchanged."""
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
        return "Nothing to change."
    rbx().update_item(KINDS[kind], universe_id, item_id, fields, read_icon(icon_path))
    return f"Updated {item_id}: {', '.join(fields) or 'icon'}"


@tool
def disable_item(kind: Kind, universe_id: int, item_id: int) -> str:
    """'Deletes' a developer product / game pass by taking it off sale (the Roblox API has no real delete)."""
    rbx().update_item(KINDS[kind], universe_id, item_id, {"isForSale": "false"})
    return f"{item_id} taken off sale."


@tool
def copy_items(kind: Literal["dev", "pass", "all"], source_universe_id: int, target_universe_id: int,
               dry_run: bool = True, copy_icons: bool = False) -> str:
    """Copies / syncs developer products and/or game passes from source to target (matched by name): creates
    missing ones and updates differing price/description/for sale/managed pricing. Returns the log and the
    old ID -> new ID mapping."""
    if source_universe_id == target_universe_id:
        raise Abort(t("same_game"))
    log = io.StringIO()
    # stdout is the MCP protocol channel - capture copy_kind's log into a string
    with contextlib.redirect_stdout(log):
        for key in (["dev", "pass"] if kind == "all" else [kind]):
            copy_kind(rbx(), key, source_universe_id, target_universe_id, dry_run, copy_icons,
                      delay=1.0, interactive=False)
    return log.getvalue()


if __name__ == "__main__":
    server.run()
