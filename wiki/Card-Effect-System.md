# Card Effect System — Reverse Engineering Notes

## Overview

The card effect system in Yu-Gi-Oh! GX Duel Academy uses a **multi-layer state machine architecture** with **three levels of dispatch**:

1. **Generic Effect Dispatch** — Two tables (execute + condition) at `0x0805034C` / `0x08050C2C` for IDs `0x62`–`0x80` (98–128). Handles standard effect types shared across all cards (draw, discard, tribute, destroy, etc.).

2. **Card-Specific Effect Dispatch** — A second parallel table at `0x0805A798` (same 31 IDs), with handlers that override the generic ones for specific cards. Referenced via a **Card Data Table** at `0x097DA800` that maps each card ordinal ID to its effect handler (defaulting to a no-op handler at `card_effect_handler_no_effect` `0x08061629` for cards with no special override).

3. **Target List Filter Functions** — ~111 functions in range `0x0805B7D8`–`0x0805F3E0` that scan player card zones, match card types/attributes against bitfield criteria, compare card IDs against hardcoded values, and update the effect register.

## Memory Layout

| Region | Address | Description |
|--------|---------|-------------|
| Global effect state | `IWRAM 0x0201FD00` | Tracks resolution state, current effect ID at `+0x7C6` |
| Player card data | `IWRAM 0x02022250` | 5 zones × 5 slots × 0x50 bytes = 0x50 per slot |
| Opponent card data | `IWRAM 0x02022250 + 0x2B08` | Same layout as player |
| Effect dispatch table 1 | `ROM 0x0805034C` | 31 fn pointers (generic execution) |
| Effect dispatch table 2 | `ROM 0x08050C2C` | 31 fn pointers (generic condition) |
| Card-specific effect table | `ROM 0x0805A798` | 31 fn pointers (card-specific overrides) |
| Card data table | `ROM 0x097DA800` | Maps card ordinal IDs to effect handlers |

## Dispatch Tables

### Table 1 — Effect Execution (`0x0805034C`)

Called by `FUN_080502FC` (`0x080502FC`). Reads effect ID from state, dispatches.

| Index | ID | Address | Handler |
|-------|-----|---------|---------|
| 0 | 0x62 (98) | `0x080507E8` | Draw/X discard from hand |
| 1 | 0x63 (99) | `0x08050764` | Deck top discard |
| 2–29 | 0x64–0x7B (100–123) | `0x0805085C` | No-op (returns 0) |
| 30 | 0x7C (124) | `0x080505D4` | Monster Tribute |
| — | 0x7D (125) | `0x08050544` | Position Change |
| — | 0x7E (126) | `0x08050468` | Destruction |
| — | 0x7F (127) | `0x08050418` | ATK Change (deck search) |
| — | 0x80 (128) | `0x080503C8` | Special Summon |

### Table 2 — Condition Check (`0x08050C2C`)

Called by `FUN_08050BEC` (`0x08050BEC`). Returns boolean (can effect activate?).

| Index | ID | Address | Handler |
|-------|-----|---------|---------|
| 0 | 0x62 (98) | `0x08051004` | Condition: draw/discard possible |
| 1 | 0x63 (99) | `0x08050F40` | Condition: deck has cards |
| 2–29 | 0x64–0x7B (100–123) | `0x08051078` | Always true |
| 30 | 0x7C (124) | `0x08050EB0` | Condition: valid tribute target exists |
| — | 0x7D (125) | `0x08050E20` | Condition: position change valid |
| — | 0x7E (126) | `0x08050D44` | Condition: destruction target valid |
| — | 0x7F (127) | `0x08050CF8` | Condition: ATK change target exists |
| — | 0x80 (128) | `0x08050CA8` | Condition: special summon possible |

### No-op Default (`0x0805085C`)

The function at `0x0805085C` simply returns `0`. It is shared by all unused effect IDs 0x64–0x7B. The corresponding condition checker at `0x08051078` returns `1` (always true).

## State Machines

The hierarchy is: **Screen → Phase → Battle**. The game uses four nested/interacting state machines:

### 1. Duel Screen State Machine (`state_machine_duel_screen` at `0x08007504`)

15 cases — screen-level handler for the "in-duel" view. Manages screen setup, draw/animation sequences, and UI transitions. Cases 0–10 handle setup/teardown, case 11 initiates the draw, case 12 handles phase transitions, **case 13 calls `state_machine_duel_phases`**, and case 14 does cleanup. Used for ALL duel types (free duels, story, practical exams — exam theme grading is at the screen level, not the phase level).

### 2. Duel Phase State Machine (`state_machine_duel_phases` at `0x0806203C`)

31 cases (6 unique) — turn phase flow. Controls: draw phase, main phase 1, battle phase, main phase 2, end phase. Delegates battle sub-steps to `state_machine_battle_phase`. Common to all duels.

### 3. Battle Phase State Machine (`state_machine_battle_phase` at `0x08064C1C`)

22 cases — handles combat: attack declaration, damage calculation, monster destruction, replay. Integrates with the effect system for battle-related effects.

### 4. Effect Resolution State Machine (`state_machine_effect_resolution` at `0x080577E8`)

6 cases — manages the effect resolution chain:
1. Check conditions → build list of activatable effects
2. Let player select effect (via UI state machine)
3. Resolve effect (execute handler)
4. Check for chain responses
5. Continue chain or return to game flow
6. Cleanup / state transition

### 5. Effect Selection UI State Machine (`state_machine_effect_selection_ui` at `0x08055A98`)

14 cases — the UI that presents effect choices to the player. Uses dialog functions for prompts.

## Card Data Structure

Per-card slot: **0x50 bytes** (at player card data base + slot_index * 0x50).

Fields include:
- Card ID
- Current zone (hand, field, GY, banished, deck)
- Position (attack/face-down defense/face-up defense)
- ATK/DEF (current, may differ from base due to effects)
- Effect flags bitmask
- Equip card reference
- Toggle counters/timers

## Dialog/UI Functions

| Address | Name | Description |
|---------|------|-------------|
| `0x08009744` | `ask_question` | Show a question prompt and await response |
| `0x08009754` | `ask_multiple` | Show multi-option selection prompt |
| `0x08009764` | `ask_yes_or_no_question` | Yes/no dialog (wrapper around ask_question) |

These are called by the effect selection state machine to present effect activation choices to the player.

## Named Functions (Ghidra Annotations)

All functions below have been renamed in Ghidra via MCP.

### Effect Dispatch (entry points)

| Ghidra Name | Address | Description |
|-------------|---------|-------------|
| `effect_dispatch_execute` | 0x080502FC | Entry: reads effect ID from state, dispatches via Table 1 |
| `effect_dispatch_condition` | 0x08050BEC | Entry: reads effect ID, dispatches via Table 2 |

### State Machines

| Ghidra Name | Address | Description |
|-------------|---------|-------------|
| `state_machine_duel_screen` | 0x08007504 | 15 cases — screen-level duel handler; case 13 calls duel_phases |
| `state_machine_duel_phases` | 0x0806203C | 31 cases (6 unique) — turn phase flow (draw, main1, battle, main2, end) |
| `state_machine_battle_phase` | 0x08064C1C | 22 cases — combat flow |
| `state_machine_effect_resolution` | 0x080577E8 | 6 cases — effect resolution chain |
| `state_machine_effect_selection_ui` | 0x08055A98 | 14 cases — effect choice UI |

### Core Effect Logic

| Ghidra Name | Address | Description |
|-------------|---------|-------------|
| `effect_activation_gatekeeper` | 0x080317E4 | Checks if targeting/activation is valid |
| `check_player_can_activate_effects` | 0x0806DF7C | Gatekeeper: checks state flags + confirmation dialogs |
| `card_type_classifier` | 0x0804FB3C | Binary-search card type LUT at 0x097D9678 |
| `targeting_mode_filter` | 0x0804FC14 | Determines targeting mode(s) between source and target cards |
| `validate_target_list` | 0x0804FDD8 | Validates a pre-built target list against effect requirements |
| `build_target_list_exec` | 0x0804FFC0 | Target list builder (execute path) |
| `build_target_list_condition` | 0x08050894 | Target list builder (condition check path) |
| `effect_targeting_dispatch` | 0x080500F0 | Effect execution dispatch (bubble-sorts by ATK, finds valid target) |
| `effect_condition_dispatch` | 0x08050988 | Condition check dispatch (bubble-sorts by ATK, checks special types) |
| `validate_target_list_strict` | 0x080500C8 | Thin wrapper: validate_target_list with max-count enforcement |
| `validate_target_list_strict_cond` | 0x0805086C | Identical wrapper for condition path |
| `build_deduped_target_list` | 0x08076010 | Builds deduplicated target list |

### Card Database

| Ghidra Name | Address | Description |
|-------------|---------|-------------|
| `get_card_name` | 0x0800DD00 | Resolves card ordinal ID → name string |
| `card_type_classifier` | 0x0804FB3C | Binary search card type LUT |
| `clear_zone_effects` | 0x0800B89C | Iterates a zone, removes all cards from effect register |
| `remove_card_from_effect_register` | 0x0800B640 | Removes a single card from active effect tracking |

### Graphics / Dialogue

| Ghidra Name | Address | Description |
|-------------|---------|-------------|
| `init_effect_dialogue` | 0x080875F4 | Initializes dialogue box display system |
| `draw_dialogue_text` | 0x08021FE8 | Queue-based text rendering for dialogue |
| `draw_dialogue_number` | 0x08022034 | Queue-based number rendering (ATK, LP, etc.) |
| `show_effect_activation_dialogue` | 0x0800870C | Formats and dispatches effect activation messages |
| `card_pile_background_load` | 0x080AD2B4 | Loads 4bpp tiled background into VRAM |

### Summon / Monster Placement

| Ghidra Name | Address | Description |
|-------------|---------|-------------|
| `record_monster_summon` | 0x0806C670 | Records a monster entering the field (face-up) |
| `record_monster_set` | 0x0806C7C4 | Records a monster set to field (face-down) |
| `fusion_summon_dialogue` | 0x0806BC00 | Fusion summon success dialogue + state flags |

### Effect Resolution / Post-Processing

| Ghidra Name | Address | Description |
|-------------|---------|-------------|
| `send_card_to_graveyard` | 0x08015DC8 | Moves card to GY or banishment with flags |
| `cleanup_card_actions` | 0x0801848C | Flushes pending card actions |
| `process_card_actions` | 0x08016AEC | Main action executor (~0x660 bytes, handles ~15+ action types) |
| `count_empty_field_slots` | 0x08010F4C | Counts empty hand/field slots |
| `show_confirmation_prompt` | 0x08010BBC | Yes/no confirmation prompt wrapper |

### Pre-named (no change needed)

| Address | Name |
|---------|------|
| 0x08009744 | `ask_question` |
| 0x08009754 | `ask_multiple` |
| 0x08009764 | `ask_yes_or_no_question` |
| 0x08009778 | `ask_binary_question` |
| 0x080097F8 | `ask_card_position_dialogue` |
| 0x0800895C | `duelist_announcing_move` |

## Call Graph

```
FUN_0800496c (sub_screen_dispatch: 0x41, 0x50=duel, 0x81)
  └── state_machine_duel_screen (0x08007504)  [15 cases: duel screen setup/teardown/run]
        ├── [case 0-10: setup, animation, UI operations]
        ├── [case 11: draw phase init]
        ├── [case 12: phase transition check via FUN_08061f14]
        ├── [case 13: calls state_machine_duel_phases]  ◄── MAIN LOOP
        │     └── state_machine_duel_phases (0x0806203C)  [31 cases: turn flow]
        │           ├── [case 0: phase advance (clear flags, increment counter)]
        │           ├── [case 1: draw phase (AI auto, player prompt)]
        │           ├── [case 10: end phase (cleanup state)]
        │           ├── [case 20: main phase / card selection]
        │           ├── [case 21: battle cleanup]
        │           ├── [case 30: draw card animation]
        │           ├── [default: draw UI, return 1]
        │           └── state_machine_battle_phase (0x08064C1C)  [22 cases: combat]
        │                 └── (integrates with effect system)
        └── [case 14: duel end/cleanup]

Effect system (called from phases):
  state_machine_effect_selection_ui (0x08055A98)  [14 cases]
    └── effect_dispatch_condition (0x08050BEC)
          ├── effect_condition_dispatch (0x08050988)
          │     ├── effect_activation_gatekeeper (0x080317E4)
          │     │     └── check_player_can_activate_effects (0x0806DF7C)
          │     │           └── show_confirmation_prompt (0x08010BBC)
          │     ├── build_target_list_condition (0x08050894)
          │     │     ├── card_type_classifier (0x0804FB3C)
          │     │     ├── count_empty_field_slots (0x08010F4C)
          │     │     └── targeting_mode_filter (0x0804FC14)
          │     └── references LUTs: card_type (0x097D9678), monster_type (0x08F243CC)
          └── [inline condition checks for IDs 0x62-0x63, 0x7C-0x80]

  state_machine_effect_resolution (0x080577E8)  [6 cases]
    └── effect_dispatch_execute (0x080502FC)
          ├── effect_activation_gatekeeper (0x080317E4)
          ├── build_target_list_exec (0x0804FFC0)
          │     ├── card_type_classifier (0x0804FB3C)
          │     ├── count_empty_field_slots (0x08010F4C)
          │     ├── targeting_mode_filter (0x0804FC14)
          │     └── validate_target_list (0x0804FDD8)
          ├── effect_targeting_dispatch (0x080500F0)
          │     └── build_target_list_exec (0x0804FFC0)
          └── [inline handlers for IDs 0x62-0x63, 0x7C-0x80]
                ├── record_monster_summon (0x0806C670) / record_monster_set (0x0806C7C4)
                ├── send_card_to_graveyard (0x08015DC8)
                ├── show_effect_activation_dialogue (0x0800870C)
                ├── init_effect_dialogue (0x080875F4)
                └── clear_zone_effects (0x0800B89C)
```

## Key Data Tables (annotated in Ghidra)

| Address | Ghidra Label | Description |
|---------|-------------|-------------|
| 0x0805034C | `effect_dispatch_table_execute` | 31 fn pointers for effect execution |
| 0x08050C2C | `effect_dispatch_table_condition` | 31 fn pointers for condition checks |
| 0x087A8624 | `LUT_ordinal_id_to_card_id` | 1201 × uint16 LE |
| 0x097D9678 | `LUT_card_type_category` | 80 × 16 bytes, binary-searched |
| 0x08F243CC | `LUT_monster_type_attributes` | 1201 × uint32 |
| 0x02022250 | `EWRAM_duel_player_data` | 2 players × 0x2B08 bytes |
| 0x0201FD00 | `IWRAM_effect_context` | Effect ID at +0x7C6 |
| 0x092515F4 | `card_pile_background_table` | 8 entries, 4bpp tiled |
| 0x0945C338 | `card_filter_icons_tiles` | 24 tiles, 2 rows (top/bottom) |
| 0x0945C318 | `card_filter_icons_palette` | Static palette for filter icons |
| 0x0945C958 | `selection_outline_top_c` | Wide Selection Outline — Top |
| 0x0945D138 | `selection_outline_bot_c_1` | Wide Selection Outline — Bot part 1 |
| 0x0945D278 | `selection_outline_bot_c_2` | Wide Selection Outline — Bot part 2 |
| 0x0945D3B8 | `selection_outline_bot_c_3` | Wide Selection Outline — Bot part 3 |
| 0x091F24DC | `character_bitmaps` | 29 duelists × 5 poses |
| 0x09250780 | `character_palettes` | Character palette data |
| 0x090A0610 | `token_pointer_table` | 14 token entries |
| 0x09772E14 | `location_thumb_pointer_table` | 3 periods × 26 locations |

## Related Functions (unexplored)

There are ~141 functions in the range `0x08055A30`–`0x0805F3E0` that likely correspond to individual card effect implementations — activated effects, continuous effects, trigger effects, etc. These have not been disassembled yet.

## Integration with Sprite System

The effect system uses card pile backgrounds (`card_pile_background()`, 8 entries, 4bpp tiled at `0x092515F4`) and selection outlines (`selection_outlines()`) for the UI layer during effect selection.

## Files

Disassembly dumps are in `dumps/effects/`:
- `dispatch_entry.S` — FUN_080502FC (effect dispatch entry point)
- `dispatch_condition.S` — FUN_08050BEC (condition check entry)
- `dispatch_tables.txt` — raw table data
- `handler_0x62.S`–`handler_0x80.S` — unique effect handlers
- `handler_default.S` — no-op handler (0x0805085C)
- `state_machine_effect_resolution.S` — FUN_080577E8
- `dumps/effects/README.md` — quick-reference table
