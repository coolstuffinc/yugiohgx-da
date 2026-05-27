# Card Data Structure

## Card Stats Table (`CARD_STATS`)

**Address**: `0x08F243CC` · **Size**: `1201 × uint32` (4804 bytes)  
**Ghidra label**: `CARD_STATS_TABLE` · **Coverage**: `CARD_STATS`

A compact 32-bit bitfield encoding all monster stats and spell/trap subtyping.

### Bitfield Layout

```
 31  30  29 │ 28  27  26  25 │ 24  23  22  21  20 │ 19  18 │ 17  16  …   9 │  8   7  …   0
────────────┼───────────────┼────────────────────┼────────┼───────────────┼───────────────
 Attribute  │    Level      │   Type / Category   │  Cat   │   ATK / 10    │   DEF / 10
  (3 bits)  │   (4 bits)    │     (5 bits)        │(2 bits)│   (9 bits)    │   (9 bits)
```

### Field Breakdown

| Bits | Width | Field | Values |
|------|-------|-------|--------|
| 0–8 | 9 | DEF ÷ 10 | 0–511 (×10 = actual DEF) |
| 9–17 | 9 | ATK ÷ 10 | 0–511 (×10 = actual ATK) |
| 17 | 1 | *Spell/Trap flag* | Equip (spells) / Counter (traps) — see below |
| 18–19 | 2 | Category | **Monsters**: 0=Normal, 1=Effect, 2=Fusion, 3=Ritual |
| 20–24 | 5 | Type | 1=Dragon … 20=Reptile, **21=Trap**, **22=Spell** |
| 25–28 | 4 | Level | 1–12 (monsters only) |
| 29–31 | 3 | Attribute | 1=LIGHT, 2=DARK, 3=WATER, 4=FIRE, 5=EARTH, 6=WIND |

### Type Codes (Monsters)

| Code | Type | Code | Type |
|------|------|------|------|
| 1 | Dragon | 11 | Beast |
| 2 | Zombie | 12 | Beast-Warrior |
| 3 | Fiend | 13 | Plant |
| 4 | Pyro | 14 | Aqua |
| 5 | Sea Serpent | 15 | Warrior |
| 6 | Rock | 16 | Winged Beast |
| 7 | Machine | 17 | Fairy |
| 8 | Fish | 18 | Spellcaster |
| 9 | Dinosaur | 19 | Thunder |
| 10 | Insect | 20 | Reptile |

### Spells (type code 22)

| b18–19 | b17 | Subtype |
|--------|-----|---------|
| 0 | — | Normal Spell |
| 1 | 0 | Field Spell |
| 1 | 1 | Equip Spell |
| 2 | 0 | Continuous Spell |
| 2 | 1 | Quick-Play Spell |
| 3 | — | Ritual Spell |

### Traps (type code 21)

| b18–19 | b17 | Subtype |
|--------|-----|---------|
| 0 | 0 | Normal Trap |
| 0 | 1 | Counter Trap |
| 2 | — | Continuous Trap |

## Related Tables

| Address | Label | Description |
|---------|-------|-------------|
| `0x087A8624` | `CARD_NUMBER_TO_ID` | Ordinal → internal card ID (1201 × uint16) |
| `0x087A8F88` | `CARD_PASSWORD_KEYS` | 8-digit password decryption keys (1201 × uint32) |
| `0x08F243CC` | `CARD_STATS_TABLE` | Card stats bitfield (1201 × uint32) — this page |
| `0x097D9678` | `LUT_card_type_category` | Card type category LUT (80 × 8 bytes, binary-searched) |
| `0x097DA800` | — | Card-specific effect handler table (~887 × 28 bytes) |

## CLI Usage

```sh
# Decode a card's stats
uv run ygogxda card lookup --rom ygogxda.gba --ordinal 1 --stats

# Patch a card's stats fields
uv run ygogxda card patch --rom ygogxda.gba --ordinal 2 --category fusion --output patched.gba
uv run ygogxda card patch --rom ygogxda.gba --ordinal 13 --atk 3000 --def 2500 --level 8 --attribute dark --type dragon --output patched.gba
```
