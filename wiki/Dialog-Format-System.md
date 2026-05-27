# Dialog Format System

The game uses two different format-string systems for dialog and UI text.

### 1. Main Format Processor (0x080BBEB4)

`format_text_processor` at `0x080BBEB4` is a complex, recursive stack-based parser used for large dialog blocks. It supports nested format codes.

#### `$` Codes — Content Insertion

These insert dynamic content into dialog strings. Format: `$<LETTER><DIGITS>` where `<DIGITS>` count varies by code type.

| Code | Digits | Length | Function | Description |
|------|--------|--------|----------|-------------|
| `$m` | 5 | 7 | `game_ui_string_by_id` | UI string from `ui_en` table by index |
| `$c` | 4 | 6 | `get_ordinal_id` + card name table | Card name by ordinal |
| `$l` | 2 | 4 | `get_rank_title` | Duelist rank/title |
| `$y` | 1 | 3 | `get_dorm_text` | Dorm name |
| `$s` | 2 | 4 | `load_place_name` | Place/location name (26 entries at `0x080BB66C`) |
| `$S` | 2 | 4 | `load_area_name` | Area/scene name |
| `$P` | 2 | 4 | `load_duelist_full_name` | Duelist full name |
| `$p` | 2 | 4 | `load_duelist_short_name` | Duelist short name |

#### `#` Codes — Inline Formatting

Handled by `handle_hash_format_codes` at `0x080BBAC8`.

| Code | Length | Effect |
|------|--------|--------|
| `#r` | 2 | Newline (return) |
| `#k` | 2 | Newline (continue) |
| `#n` | 2 | Newline |
| `#e` | 2 | End/ellipsis |
| `#><N>` | 3+ | EWRAM deref |

### 2. Simple Format Processor (0x080C1C38)

`simple_text_format_processor` at `0x080C1C38` is a linear parser used for simpler UI elements. It supports a subset of codes and can optionally wrap results in `@3...@7` formatting markers.

Supports: `$l, $y, $m, $p, $s` and basic `#` newlines.


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

## Dialog Display Pipeline

```
Dialog strings (ui_en table with $ format codes)
    │
    ▼
dialog_format_setup (0x080BD4B0) — loads string by index, creates dialog state struct
    │
    ▼
format_text_processor (0x080BBEB4) — resolves $ codes, calls appropriate resolvers
    │
    ▼
Text rendering functions — draw text to screen, handle # format codes
```

## Dialog State Machines

These functions manage dialog flow when interacting with NPCs, the shop, etc.

| Address | Name | Role |
|---------|------|------|
| `0x080A19B4` | `dialog_show_with_duelist_portrait` | Shows dialog with string + optional duelist portrait (2 slots) |
| `0x080A1CEC` | `dialog_batch_loader_sm` | ~10-state machine: loads multiple strings, shows dialog, waits for input |
| `0x080A1AEC` | `dialog_interact_selector_sm` | State machine for interaction choice selection (accept/reject duelist approach) |
| `0x080A182C` | `dialog_show_reserve` | Shows dummy dialog with string index 0 (reserve) |

## Dialog Helpers

| Address | Name | Role |
|---------|------|------|
| `0x080BD4B0` | `dialog_format_setup` | Allocates dialog state struct, loads string by index |
| `0x080BD5D4` | `dialog_set_text_alignment` | Sets alignment: 0=left, 1=center, 2=right |
| `0x080BD550` | `dialog_update_and_check_busy` | Advances animation, returns 0=busy, 1=done |
| `0x080BD62C` | `dialog_set_portrait_id` | Sets duelist portrait/sprite ID (1-255) |

## Format String Resolvers

| Address | Name | Role |
|---------|------|------|
| `0x080BB628` | `game_ui_string_by_id` | Loads string from `ui_en` table by index |
| `0x080BBEB4` | `format_text_processor` | Main format string parser and renderer |
| `0x080BBB34` | `get_format_code_arg_length` | Returns format code type and arg length |
| `0x080BBAC8` | `handle_hash_format_codes` | Handles `#r`/`#k`/`#n`/`#e`/`#>` codes |
| `0x080BBCD8` | `push_format_stack` | Pushes onto format resolution stack |
| `0x080BBCF4` | `pop_format_stack` | Pops from format resolution stack |
| `0x080BD660` | `parse_decimal_digits` | Parses N decimal digits to integer |
| `0x080BB654` | `load_place_name` | `$s` handler: place/location name |
| `0x080BB670` | `load_area_name` | `$S` handler: area/scene name |
| `0x080BB72C` | `load_duelist_full_name` | `$P` handler: duelist full name |
| `0x080BB754` | `load_duelist_short_name` | `$p` handler: duelist short name |

## Dialog Consumers

| Address | Name | Role |
|---------|------|------|
| `0x0809FAB8` | `show_morning_thought` | Protagonist's morning thought (weekday/weekend/school start) |
| `0x080C91E0` | `timed_duel_rules_popup_sm` | Timed Duel rules popup state machine |
| `0x080C9308` | `timed_duel_selection_sm` | Timed Duel parent selection state machine |
| `0x080C8B30` | `timed_duel_pack_choice_sm` | Timed Duel pack choice state machine |
| `shop_service` / `shop_dialogue_show` | Shop dialog with inline string literals |
