# 💰 Roblox Monetization Handler And Image Uploader MCP

A Python tool for copying and syncing **developer products** and **game passes** between Roblox experiences, without an Open Cloud API key. It signs in with your `.ROBLOSECURITY` cookie and uses the same `apis.roblox.com` endpoints as the Creator Dashboard.

It ships with an **MCP server**, so AI assistants such as Claude Code can list, create, update and disable products for you.

---

## ✨ Features

- **Copy developer products and game passes** from one experience to another: name, description, price, for-sale status, managed pricing and, optionally, the icon.
- **Sync existing items.** Items are matched by name. If an item already exists in the target experience but its price, description, for-sale status or managed pricing differs, it is updated to match the source.
- **Safe to re-run.** Items that already match are skipped, so you can run it again after an error without creating duplicates.
- **Preview before changing anything.** Every item is shown as `NEW`, `CHANGE: …` or `unchanged`, and the tool asks for confirmation.
- **Old → new ID mapping** saved as JSON and as a Lua table, ready to paste into your game scripts (`ProcessReceipt`, `PromptProductPurchase`, `UserOwnsGamePassAsync`).
- **List names and IDs** of all developer products and game passes in an experience, saved to `.txt` and to a Lua `["name"] = id` table.
- **Managed Pricing fallback.** If the target experience hasn't accepted Managed Pricing, items are created without it. Accept it in the dashboard and run the tool again to turn it on.
- **Upload images as decals** (single files or whole folders) and get each one's **image ID**, the one `ImageLabel.Image` / `rbxassetid://` needs. The name → image ID mapping is saved to JSON and a Lua table.
- **Handles CSRF tokens and rate limits** automatically.

---

## 📦 Installation

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

---

## 🔑 Authentication

The tool needs the `.ROBLOSECURITY` cookie of an account that can manage both experiences. It looks for it in this order:

1. The `ROBLOSECURITY` environment variable.
2. A `cookie.txt` file next to the script.
3. A prompt when the tool starts. Input is hidden. This option isn't available to the MCP server.

To get the cookie, open roblox.com, press F12, go to **Application → Cookies → `https://www.roblox.com`** and copy the value of `.ROBLOSECURITY`.

> ⚠️ **The cookie gives full access to your Roblox account.** Never share it or commit it. `cookie.txt` is already in `.gitignore`.

---

## 🚀 Usage

### Interactive menu

Double-click `Uruchom.bat` or run:

```bash
python copy_devproducts.py
```

```text
1) Copy / update developer products
2) Copy / update game passes
3) Copy / update both
4) Print names and IDs (developer products + game passes)
5) Upload images (decals) -> image IDs
9) Language: English
0) Exit
```

The tool asks for **universe IDs**, not place IDs. You'll find the universe ID in the Creator Dashboard URL: `create.roblox.com/dashboard/creations/experiences/<universeId>/...`.

### 🌐 Language

The tool is in **English** by default and also available in **Polish**. Switch with option `9` in the menu or from the command line:

```bash
python copy_devproducts.py lang pl   # or: lang en
```

Your choice is saved to `settings.json` and remembered for the next run, including messages returned by the MCP server.

### Command line

```bash
# Preview without changing anything
python copy_devproducts.py copy dev  SOURCE_ID TARGET_ID --dry-run

# Copy game passes, including icons
python copy_devproducts.py copy pass SOURCE_ID TARGET_ID --icons

# Copy both
python copy_devproducts.py copy all  SOURCE_ID TARGET_ID

# Print names and IDs
python copy_devproducts.py list all  UNIVERSE_ID

# Upload images as decals (files or folders), print their image IDs
python copy_devproducts.py upload "C:/Icons" extra.png
python copy_devproducts.py upload "C:/Icons" --group GROUP_ID
```

| Option | Description |
|---|---|
| `--dry-run` | Show what would change, change nothing |
| `--icons` | Copy icons to newly created items |
| `--delay` | Pause between requests in seconds (default `1.0`) |
| `--group` | `upload` only: upload to this group instead of your account |

### Output files

| File | Contents |
|---|---|
| `mapping_devproducts_<src>_to_<dst>.json` / `.lua` | Old developer product ID → new ID |
| `mapping_gamepasses_<src>_to_<dst>.json` / `.lua` | Old game pass ID → new ID |
| `lists/list_devproducts_<id>.txt` / `.lua` | Names, prices and IDs of developer products |
| `lists/list_gamepasses_<id>.txt` / `.lua` | Names, prices and IDs of game passes |
| `lists/images_<time>.json` / `.lua` | Uploaded images: name → decal ID and image ID (`["name"] = "rbxassetid://<image>"`) |

Example Lua mapping:

```lua
return {
	[3712165792] = 3745012345, -- LESS COOLDOWN!
	[3712165749] = 3745012346, -- CUSTOM COUNTRY!
}
```

---

## 🤖 MCP Server

`mcp_server.py` exposes the tool over MCP (stdio), so an AI assistant can manage your monetization directly.

| Tool | What it does |
|---|---|
| `list_items` | Lists developer products (`dev`) or game passes (`pass`) in an experience |
| `create_item` | Creates a developer product or game pass, optionally with an icon from a local file |
| `update_item` | Changes selected fields: name, description, price, for sale, managed pricing, icon |
| `disable_item` | Takes an item off sale |
| `copy_items` | Copies or syncs items between experiences. Defaults to a dry run |
| `upload_images` | Uploads image files or folders as decals; returns each decal ID and image ID |

### Setup with Claude Code

1. Put your cookie in `cookie.txt` or set the `ROBLOSECURITY` environment variable. The MCP server can't prompt for it.
2. Register the server:

   ```bash
   claude mcp add --scope user roblox-monetization -- python "C:/path/to/mcp_server.py"
   ```

3. Restart Claude Code, then ask things like:
   - *"Create a game pass called VIP for 299 Robux in experience 10773645374"*
   - *"Copy all game passes from 10480068191 to 10773645374"*
   - *"Raise the price of every developer product in 10773645374 by 20%"*

Other MCP clients work too: run `python mcp_server.py` as a stdio server.

---

## ⚠️ Limitations

- **Roblox doesn't allow deleting** developer products or game passes. The closest option is taking them off sale (`disable_item`).
- **Items are matched by name.** Renaming an item in the source creates a new one in the target instead of updating the old one.
- **Icons aren't compared.** They are copied only when an item is created.
- **Localized names and descriptions aren't copied.**
- **The endpoints are in Beta** on Roblox's side and may change.

---

## 📁 Project Structure

```text
copy_devproducts.py   # Core logic, interactive menu and CLI
mcp_server.py         # MCP server (stdio)
i18n.py               # English / Polish translations, language saved to settings.json
Uruchom.bat           # Windows launcher for the menu
requirements.txt      # requests, mcp
```
