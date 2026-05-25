# Exam Question Database

**Address**: GBA 0x09430be0-0x09430f0f (offset table)  
**Address**: GBA 0x09430f10-??? (card data structures)  
**ROM offset**: 0x01430be0 (table), 0x01430f10 (data)

## Structure

Accessed via two pointer tables:
- `PTR_DAT_080a68bc` → points to `0x09430be0` (offset table)
- `PTR_DAT_080a68c0` → points to `0x09430f10` (base of card data)

Also referenced by: `FUN_080a6850`, `FUN_080a7000`, `FUN_080a7374`
(via pointers at 0x080a68bc, 0x080a706c, 0x080a741c)

### Offset Table
Array of uint32 LE at `0x09430be0`. Contains 1200 entries (indices 0-1199).
Each entry is an offset from `0x09430f10` to the start of a card data structure.

### Card Data Structure
Each entry at `0x09430f10 + offset_table[i]` has this layout:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00   | u16  | type  | Structure type: 0x2231=exam_about_card, 0x2232=exam_grouping, 0x2021=sentinel |
| 0x02   | u16  | card_id | Card passcode number (e.g., 4007 for Blue-Eyes) |
| 0x04   | u16  | ?     | Usually 0 |
| 0x06   | u16  | ?     | Usually 0 |
| 0x08   | u16  | ?     | Usually 0 |
| 0x0a   | u16  | answer1 | Answer option 1 identifier |
| 0x0c   | u16  | answer2 | Answer option 2 identifier |
| 0x0e   | u16  | answer3 | Answer option 3 identifier |
| 0x10   | u16  | ?     | Usually 0 |
| 0x12   | u16  | str_off | Offset from start of structure to template string |
| 0x14+  | -    | -     | Variable-length template string area |

### Template Strings
The template strings use the following placeholders (processed by `replace_cardname_in_template` at `0x080a6634`):
- `$XXXX` — 4-digit card passcode number, replaced with card name
- `%1`-`%8` — references fields from the card stats struct passed as param_1:
  - `%1` → offset 2, `%2` → offset 4, `%3` → offset 6, `%4` → offset 8
  - `%5` → offset 10
  - `%6` → offset 12, `%7` → offset 14, `%8` → offset 16
  - Values < 10: attribute index (looked up at PTR_monster_attributes @ 0x097d7b9c)
  - Values 100-129: monster type index (looked up at DAT_080a66d4 → 0x097d7b38)
  - Values > DAT_080a66b8 (0x3e7 = 999): treated as card ID
- `^XXX` — reference to another exam entry (^001 references entry with offset index 1)
- `#S`, `#M1`, `#M2`, `#P` — dialogue template markers (processed by `replace_monster_or_spell_in_template`)

### Known Entries

| Index | Card ID | Type | Template |
|-------|---------|------|----------|
| 0 | 4062 | 0x2021 | "Dummy Examination" |
| 1 | 4007 | 0x2231 | "Which monster has a Flip Effect?" |
| 2 | 0 | 0x2232 | "^001" |
| 3 | 4010 | 0x2231 | "^001" |
| 4 | 4728 | 0x2231 | "What do you need to Ritual Summon \"%1\"?" |
| 5 | 5697 | 0x2231 | "^004" |
| 6 | 4737 | 0x2231 | "^004" |
| 7 | 0 | 0x2231 | "Which monster's effect does not require a coin toss?" |

### Functions That Use This Data

- `FUN_080a6850` — Reads exam question structure, calls replace_cardname_in_template
- `FUN_080a7000` — Reads card info for duel screen display (card type, attribute display)
- `FUN_080a7374` — Reads card data and renders card descriptions/info in battle
