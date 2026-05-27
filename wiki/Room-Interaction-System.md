# Room Interaction System

## Overview

The room interaction system handles PDA menu navigation and room-specific actions throughout the academy. When the player is in a room (dorm, classroom, shop, etc.), interacting with the environment triggers a screen state machine that renders a context-sensitive menu and dispatches to handler functions.

## Key Data: `ROOM_INTERACTION_TABLE`

**Address**: `0x097EDA00` · **Size**: ~1 KB  
**Ghidra label**: `ROOM_INTERACTION_TABLE` · **Coverage**: `ROOM_INTERACTION_TABLE`

The table structure (offsets from base):

| Offset | Content | Description |
|--------|---------|-------------|
| `+0x00` | 8 bytes | Header |
| `+0x08` | 12 × uint32 (48 B) | Month name string pointers (January–December) |
| `+0x38` | ~31 × uint32 (124 B) | Menu screen definition function pointers (~32 entries, some NULL) |
| `+0xC8` | ~13 × uint32 (52 B) | Menu string config pointers + other data |
| `+0xFC` | 17+ × uint32 | Room menu handler dispatch table |

### Menu Configurations

Three string configs control which menu options appear, referenced by handler code:

1. **Config 1**: Sleep / Tutorial
2. **Config 2**: PDA + Sleep + Tutorial
3. **Config 3**: PDA + Sleep + Tutorial + Timed Duel

## Screen State Machine

**Entry point**: `room_screen_state_machine` (`0x080A09B4`)

A 5-state machine controlling room screens:

| State | Description |
|-------|-------------|
| 0 | Init / entrance |
| 1 | Menu rendering |
| 2 | Handler dispatch |
| 3 | Transition / animation |
| 4 | Exit / cleanup |

### Key Functions

| Address | Ghidra Label | Purpose |
|---------|-------------|---------|
| `0x0809EF34` | `render_room_menu` | Renders the menu overlay (window + blend effects) |
| `0x080A7C68` | `dispatch_room_menu_handler` | Routes to handler via `ROOM_INTERACTION_TABLE + 0xFC` |
| `0x080A09B4` | `room_screen_state_machine` | 5-state screen machine controlling flow |
| `0x080C1C38` | `text_format_processor` | Expands format codes in UI strings (see below) |

### Handler Slots

Named handlers in Ghidra (`room_handler_slot_0` through `room_handler_slot_8`), dispatches at `ROOM_INTERACTION_TABLE + 0xFC`.

## Rank / Title System

### Duelist Titles

**Address**: `0x097F0D50` · **Size**: 14 pointers  
**Ghidra label**: `DUELIST_TITLES_EN`

14 entries (index 0 is reserved, 1–13 are used in-game):

| Index | Title |
|-------|-------|
| 0 | reserved. |
| 1 | King of Games |
| 2 | Prince of Games |
| 3 | Celebrity Duelist |
| 4 | Elite Duelist |
| 5 | Honored Duelist |
| 6 | Shrewd Duelist |
| 7 | Superior Duelist |
| 8 | Calm Duelist |
| 9 | Fiery Duelist |
| 10 | Average Duelist |
| 11 | Novice Duelist |
| 12 | Apprentice Duelist |
| 13 | Dropout Boy |

### Academy Dorms

**Address**: `0x097F0D88` · **Size**: 3 pointers

| Index | Dorm |
|-------|------|
| 0 | Slifer Red |
| 1 | Ra Yellow |
| 2 | Obelisk Blue |

### Functions

| Address | Ghidra Label | Purpose |
|---------|-------------|---------|
| `0x080BB77C` | `get_rank_title` | Returns rank string by index; called by `text_format_processor` (for `$l`) and `show_pda_screen` |
| `0x080BB7A0` | `get_dorm_text` | Returns dorm string by index; called by `text_format_processor` (for `$y`) and `show_pda_screen` |

## Text Format Processor

**Address**: `0x080C1C38` · **Ghidra label**: `text_format_processor`

Expands format codes in UI strings. When `param_4 != 0`, variable expansions are wrapped in `@3`...`@7` formatting markers (likely bold on/off).

| Code | Expansion | Notes |
|------|-----------|-------|
| `$l` | Current rank title | `get_rank_title()` — reads 2-digit index |
| `$y` | Current dorm name | `get_dorm_text()` — reads 1-digit index |
| `$m` | Player name | via `FUN_080bb654` |
| `$p` | Extra string | via `FUN_080bb754`, reads 2-digit index |
| `$s` | Extra string | via `FUN_080bb654`, reads 2-digit index |
| `$n` | Newline (0x0A) | |
| `#r` | Newline (0x0A) | Synonym for `#n` |
| `#k` | Newline (0x0A) | Synonym for `#n` |
| `#>` | Skip 7 bytes | Used for conditional/escape sequences |

## Unnamed Functions (Profile / Results)

Four entry points in the `0x080BC454`–`0x080BCB58` range that Ghidra did not auto-discover as functions. Likely profile display and result screen handlers. Documented with disassembly comments at their entry points:

- `0x080BC454` — profile status screen
- `0x080BC598` — profile detail screen
- `0x080BC86C` — result summary screen
- `0x080BCB58` — result detail screen
