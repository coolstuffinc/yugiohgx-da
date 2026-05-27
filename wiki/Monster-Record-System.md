# Monster Record System

## Overview

When a monster is Summoned, Set, or has its battle position changed, the game creates a "monster record" — a structured event log that drives the animation system, sound effects, and confirmation prompts.

## Record Buffer

**Address**: `EWRAM 0x020280F0` · **Field state base**: `EWRAM 0x02022250`

Each player has `0x2B08` bytes of field state, and each monster slot is `0x50` bytes.

### Record Structure (at `0x020280F0`)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| `+0x00` | uint16 | card_id | Internal card ID (15-bit) |
| `+0x02` | uint8 | zone_ref | Bits 0–6 = slot, bit 7 = player |
| `+0x03` | uint8 | flags | Bit 0 = face-down, bits 1–7 = extra flags |
| `+0x04` | uint16 | position | Battle position + marker bits (affected by uint32 ops) |
| `+0x05` | uint8 | extra_flags | Bit 1 = flipped/limited, bit 2 = tribute |
| `+0x08` | uint8 | op_marker | Low nibble always 7 (operation type marker) |
| `+0x5C` | uint8 | action_flags | Bit 2 always set when recording |
| `+0x5E` | uint8 | state_control | Operation bits: bit 2=reposition, bit 2+3=summon, bit 4=set |

## Functions

### Record Creators

Each function ORs a unique bit pattern into `record[0x5E]` (masked with `0xC3` first, preserving bits 0-1 and 6-7):

| Address | Ghidra Label | record[0x5E] OR | Bits | Trigger |
|---------|-------------|-----------------|------|---------|
| `0x0806C700` | `record_monster_summon` | `0x0C` | 2+3 | Normal/Special Summon |
| `0x0806C7C4` | `record_monster_set` | `0x10` | 4 | Set face-down |
| `0x0806C344` | `record_monster_reposition` | `0x04` | 2 | Position/mode change |

Each function:
1. Reads card ID from the monster's field state slot
2. Populates the record buffer at `0x020280F0`
3. Calls `process_monster_record` (`0x0806C02C`)

### `process_monster_record` (`0x0806C02C`)

A **two-phase, 8-state machine**:

**Phase 1** (states 0–3): Animation and feedback
- State 0: Init — validate record, lookup card art
- State 1: Play monster summon/Set animation
- State 2: Show ATK/DEF stat display
- State 3: Pause for confirmation key press

**Phase 2** (states 4–7): Cleanup
- State 4: Fade out stat display
- State 5: Clear record buffer
- State 6: Return to field / next action
- State 7: Complete

## Constants

| Ghidra Label | Value | Purpose |
|-------------|-------|---------|
| `PTR_FIELD_STATE` | `0x02022250` | Base address of per-player field state |
| `PTR_MONSTER_RECORD` | `0x020280F0` | Record buffer address |
| `PLAYER_FIELD_STRIDE` | `0x2B08` | Bytes per player in field state array |
| `POSITION_MASK_CLEAR` | bitmask | Clears position-related bits |
| `MASK_RECORD_STATE_CLEAR` | bitmask | Clears record state bits |
| `PTR_JUMP_TABLE_STATE_0` | function ptr | State 0 handler for the process state machine |
