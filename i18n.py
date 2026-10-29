"""Tłumaczenia EN / PL. Wybrany język jest zapisywany w settings.json obok skryptu."""

import json
from pathlib import Path

SETTINGS = Path(__file__).resolve().parent / "settings.json"
LANGUAGES = {"en": "English", "pl": "Polski"}
DEFAULT = "en"

STRINGS = {
    "en": {
        "kind_dev": "Developer products",
        "kind_pass": "Game passes",
        "rate_limit": "   rate limit, waiting {wait}s...",
        "err_401": "Error 401: cookie is invalid or expired.",
        "too_many_retries": "Too many retries: {url}",
        "fetching": "Fetching from {id}...",
        "st_new": "NEW",
        "st_change": "CHANGE: {diff}",
        "st_same": "unchanged",
        "d_price": "price {old} -> {new}",
        "d_sale": "for sale -> {v}",
        "d_managed": "managed -> {v}",
        "d_desc": "description",
        "summary": "Source: {src} | new: {new} | to update: {upd} | unchanged: {same}",
        "no_price": "WARNING: couldn't read the price. Raw data of the first item:",
        "no_price_abort": "Aborted - share this data so price_of() can be fixed.",
        "dry_run": "Dry run - nothing changed.",
        "nothing": "Nothing to do.",
        "confirm": "Create {new} and update {upd}? [y/N]: ",
        "skipped": "Skipped.",
        "ask_icons": "Copy icons to new items? [y/N]: ",
        "managed_off": "   Managed Pricing isn't accepted in the target experience - skipping that field.",
        "icon_failed": "   icon failed: {err}",
        "p_new": "[{n}/{total}] NEW  {name}  {old} -> {new}",
        "p_change": "[{n}/{total}] CHANGE  {name}",
        "p_error": "[{n}/{total}] ERROR  {name}: {err}",
        "failed": "Failed: {count} - run again, finished items will be skipped.",
        "managed_hint": "Some changes went through WITHOUT Managed Pricing. Accept it in the target experience's"
                        " dashboard (Monetization -> Managed pricing) and run again - the tool will enable it.",
        "mapping_saved": "Mapping saved: {stem}.json / .lua",
        "saved": "Saved: {stem}.txt / .lua",
        "no_cookie_mcp": "No cookie: set ROBLOSECURITY or save it to cookie.txt next to the script.",
        "paste_cookie": "Paste your .ROBLOSECURITY cookie (F12 -> Application -> Cookies -> roblox.com).",
        "hidden": "It won't be visible while pasting.",
        "no_cookie": "No cookie.",
        "number_only": "Enter a number only.",
        "m_copy_dev": "1) Copy / update developer products",
        "m_copy_pass": "2) Copy / update game passes",
        "m_copy_all": "3) Copy / update both",
        "m_list": "4) Print names and IDs (developer products + game passes)",
        "m_lang": "9) Language: {lang}",
        "m_exit": "0) Exit",
        "ask_source": "SOURCE experience universeId: ",
        "ask_target": "TARGET experience universeId: ",
        "ask_universe": "Experience universeId: ",
        "same_game": "Source and target are the same experience.",
        "lang_set": "Language set to: {lang}",
        "interrupted": "Interrupted.",
        "press_enter": "Press Enter to close...",
        "cli_desc": "Copy developer products and game passes between Roblox experiences.",
        "cli_copy": "copy / update",
        "cli_source": "source experience universeId",
        "cli_target": "target experience universeId",
        "cli_dry": "preview only, change nothing",
        "cli_icons": "copy icons to new items",
        "cli_delay": "pause between requests (s)",
        "cli_list": "print names and IDs",
        "cli_lang": "set and save the language",
    },
    "pl": {
        "kind_dev": "Developer producty",
        "kind_pass": "Gamepassy",
        "rate_limit": "   rate limit, czekam {wait}s...",
        "err_401": "Błąd 401: cookie nieważne albo wygasło.",
        "too_many_retries": "Za dużo prób: {url}",
        "fetching": "Pobieram z {id}...",
        "st_new": "NOWY",
        "st_change": "ZMIANA: {diff}",
        "st_same": "bez zmian",
        "d_price": "cena {old} -> {new}",
        "d_sale": "for sale -> {v}",
        "d_managed": "managed -> {v}",
        "d_desc": "opis",
        "summary": "Źródło: {src} | nowe: {new} | do aktualizacji: {upd} | bez zmian: {same}",
        "no_price": "UWAGA: nie udało się odczytać ceny. Surowe dane pierwszego:",
        "no_price_abort": "Przerwano - pokaż te dane, żeby poprawić price_of().",
        "dry_run": "Dry run - nic nie zmieniono.",
        "nothing": "Nic do zrobienia.",
        "confirm": "Utworzyć {new} i zaktualizować {upd}? [t/N]: ",
        "skipped": "Pominięto.",
        "ask_icons": "Kopiować ikony nowym? [t/N]: ",
        "managed_off": "   Managed Pricing nie jest zaakceptowane w grze docelowej - pomijam to pole.",
        "icon_failed": "   ikona nie poszła: {err}",
        "p_new": "[{n}/{total}] NOWY  {name}  {old} -> {new}",
        "p_change": "[{n}/{total}] ZMIANA  {name}",
        "p_error": "[{n}/{total}] BŁĄD  {name}: {err}",
        "failed": "Nie udało się: {count} - odpal ponownie, gotowe zostaną pominięte.",
        "managed_hint": "Część zmian poszła BEZ Managed Pricing. Zaakceptuj je w dashboardzie gry docelowej"
                        " (Monetization -> Managed pricing) i odpal ponownie - skrypt je włączy.",
        "mapping_saved": "Mapowanie zapisane: {stem}.json / .lua",
        "saved": "Zapisane: {stem}.txt / .lua",
        "no_cookie_mcp": "Brak cookie: ustaw ROBLOSECURITY albo zapisz je w cookie.txt obok skryptu.",
        "paste_cookie": "Wklej cookie .ROBLOSECURITY (F12 -> Application -> Cookies -> roblox.com).",
        "hidden": "Nie będzie widoczne podczas wklejania.",
        "no_cookie": "Brak cookie.",
        "number_only": "Podaj samą liczbę.",
        "m_copy_dev": "1) Kopiuj / aktualizuj developer producty",
        "m_copy_pass": "2) Kopiuj / aktualizuj gamepassy",
        "m_copy_all": "3) Kopiuj / aktualizuj oba",
        "m_list": "4) Wypisz nazwy i ID (dev producty + gamepassy)",
        "m_lang": "9) Język: {lang}",
        "m_exit": "0) Wyjście",
        "ask_source": "universeId gry ŹRÓDŁOWEJ: ",
        "ask_target": "universeId gry DOCELOWEJ: ",
        "ask_universe": "universeId gry: ",
        "same_game": "Źródło i cel to ta sama gra.",
        "lang_set": "Ustawiono język: {lang}",
        "interrupted": "Przerwano.",
        "press_enter": "Enter, żeby zamknąć...",
        "cli_desc": "Kopiowanie developer productów i gamepassów między grami Roblox.",
        "cli_copy": "kopiuj / aktualizuj",
        "cli_source": "universeId gry źródłowej",
        "cli_target": "universeId gry docelowej",
        "cli_dry": "tylko podgląd, nic nie zmienia",
        "cli_icons": "kopiuj ikony nowym",
        "cli_delay": "przerwa między zapytaniami (s)",
        "cli_list": "wypisz nazwy i ID",
        "cli_lang": "ustaw i zapisz język",
    },
}


def _load() -> str:
    try:
        lang = json.loads(SETTINGS.read_text(encoding="utf-8")).get("language")
    except (OSError, ValueError):
        return DEFAULT
    return lang if lang in STRINGS else DEFAULT


lang = _load()


def set_language(code: str) -> None:
    global lang
    lang = code
    try:
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        settings = {}
    settings["language"] = code
    SETTINGS.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def t(key: str, **kw) -> str:
    return STRINGS[lang].get(key, STRINGS[DEFAULT][key]).format(**kw)


def is_yes(answer: str) -> bool:
    return answer.strip().lower() in ("y", "yes", "t", "tak")
