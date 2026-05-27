# Dialog Format System

The game uses a format-string system for all dialog and UI text. Format strings contain `$` and `#` codes that are resolved at runtime by `format_text_processor` at `0x080BBEB4`.

## Format Code Reference

### `$` Codes — Content Insertion

These insert dynamic content into dialog strings. Format: `$<LETTER><DIGITS>` where `<DIGITS>` count varies by code type.

| Code | Digits | Length | Function | Description |
|------|--------|--------|----------|-------------|
| `$m` | 5 | 7 | `game_ui_string_by_id` | UI string from `ui_en` table by index |
| `$c` | 4 | 6 | `get_ordinal_id` + card name table | Card name by ordinal |
| `$l` | 2 | 4 | `get_rank_title` | Duelist rank/title |
| `$y` | 1 | 3 | `get_dorm_text` | Dorm name |
| `$s` | 2 | 4 | `load_place_name` | Place/location name (26 entries at `0x080BB66C`) |
| `$S` | 2 | 4 | `load_area_name` | Area/scene name (switch: Duel Academy, dorms, Ocean, Volcano, Harbor) |
| `$P` | 2 | 4 | `load_duelist_full_name` | Duelist full name (index 0 = player, 1-35 = NPCs) |
| `$p` | 2 | 4 | `load_duelist_short_name` | Duelist short name (same index range) |
| `$C` | 1 | 3 | (color?) | Unknown — 1-digit arg |
| `$$` | 0 | 2 | — | Literal `$` character |
| `$L` | 0 | 2 | — | Loads from EWRAM state |
| `$Y` | 0 | 2 | — | Dorm text variant |
| `$t` | 0 | 2 | — | Special handler |

### `@` Codes — Quick Selection

Single-digit codes `@0` through `@7`. Used for quick selection/answer highlighting in dialogs.

### `#` Codes — Inline Formatting

Handled by `handle_hash_format_codes` at `0x080BBAC8`.

| Code | Length | Effect |
|------|--------|--------|
| `#r` | 2 | Newline (return) |
| `#k` | 2 | Newline (continue) |
| `#n` | 2 | Newline |
| `#e` | 2 | (end/ellipsis?) |
| `#><N>` | 3+ | Variable-width: dereferences EWRAM pointer at offset `N` |

## Architecture

### Format Stack

`format_text_processor` uses a stack (max 8 entries) to handle nested format code resolution:

1. Character-by-character loop processes the input format string
2. When a `$` is encountered, `get_format_code_arg_length` determines the code type and digit count
3. `parse_decimal_digits` extracts the numeric argument
4. The resolved string pointer is pushed onto the format stack via `push_format_stack`
5. If the resolved string itself contains format codes, it's recursively processed
6. When finished, `pop_format_stack` restores the previous context

### Dialog Setup

`dialog_format_setup` at `0x080BD4B0`:

1. Allocates and initializes a dialog state struct
2. Calls `game_ui_string_by_id(param_1)` to load the target string
3. Stores the string pointer in the dialog state struct
4. Calls text rendering functions to display the dialog

Some callers (like `shop_dialogue_show`) bypass the string table and directly embed string literals into the dialog struct at offset `+0x40`.

## Key Functions (Annotated)

| Address | Name | Role |
|---------|------|------|
| `0x080BB628` | `game_ui_string_by_id` | Loads string from `ui_en` table by index |
| `0x080BBEB4` | `format_text_processor` | Main format string parser and renderer |
| `0x080BBB34` | `get_format_code_arg_length` | Returns format code type and arg length |
| `0x080BBAC8` | `handle_hash_format_codes` | Handles `#r`/`#k`/`#n`/`#e`/`#>` codes |
| `0x080BBCD8` | `push_format_stack` | Pushes string onto format resolution stack |
| `0x080BBCF4` | `pop_format_stack` | Pops string from format resolution stack |
| `0x080BD660` | `parse_decimal_digits` | Parses N decimal digits to integer |
| `0x080BD4B0` | `dialog_format_setup` | Dialog box initialization with ui_en string |
| `0x080BB654` | `load_place_name` | `$s` handler: place/location name |
| `0x080BB670` | `load_area_name` | `$S` handler: area/scene name |
| `0x080BB72C` | `load_duelist_full_name` | `$P` handler: duelist full name |
| `0x080BB754` | `load_duelist_short_name` | `$p` handler: duelist short name |
| `0x080C91E0` | `timed_duel_rules_popup_sm` | Timed Duel rules popup state machine |
| `0x080C9308` | `timed_duel_selection_sm` | Timed Duel parent selection state machine |
| `0x080C8B30` | `timed_duel_pack_choice_sm` | Timed Duel pack choice state machine |
