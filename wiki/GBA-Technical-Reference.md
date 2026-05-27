# GBA Technical Reference

Hardware and software conventions relevant to reverse-engineering Yu-Gi-Oh! GX Duel Academy.

## GBA Hardware Overview

| Component | Address | Size | Description |
|-----------|---------|------|-------------|
| ROM (game pak) | `0x08000000` | up to 32 MB | Game code and assets mapped here |
| IWRAM (on-chip) | `0x03000000` | 32 KB | Fast internal RAM (stack, hot data) |
| EWRAM (external) | `0x02000000` | 256 KB | Main RAM (duel state, large structures) |
| VRAM | `0x06000000` | 96 KB | Tile data, backgrounds, bitmaps |
| Palette RAM | `0x05000000` | 1 KB | 256 color entries × 2 bytes (15-bit) |
| OAM | `0x07000000` | 1 KB | 128 sprite entries × 8 bytes |

### Display

- Resolution: **240 × 160 pixels**
- Backgrounds: 4 tilemap layers (text/affine modes)
- Sprites: up to 128 hardware objects
- Color: **15-bit RGB** (BGR555 LE — bits 0-4 blue, 5-9 green, 10-14 red; bit 15 unused/transparency)

### ARM CPU

- CPU: **ARM7TDMI** (32-bit ARM + 16-bit Thumb)
- ROM runs in **ARM mode** at 16.78 MHz
- Mixed ARM/Thumb code is common; Ghidra auto-detects

## Memory Architecture (This ROM)

### Address Translation

ROM file offsets ↔ virtual addresses:

```
virtual = 0x08000000 + file_offset
file_offset = virtual - 0x08000000
```

### Key Memory Regions

| Region | Virtual Address | Size | Content |
|--------|----------------|------|---------|
| Card bitmaps | `0x087CFACC` | ~7.3 MB | 1201 cards × 6400 bytes (64×40 15-bit) |
| Card names (EN) | `0x08F25690` | ~50 KB | Null-terminated name strings |
| Card name offsets | `0x08F2A68C` | 4804 B | 1201 × uint32 LE offset table |
| Card stats | `0x08F243CC` | 4804 B | 1201 × uint32 bit-packed (ATK/DEF/level/type) |
| Card ID LUT | `0x087A8624` | 2402 B | 1201 × uint16 ordinal → card ID |
| Card passwords | `0x087A8F88` | 4804 B | 1201 × uint32 decrypt keys |
| Card type LUT | `0x097D9678` | 640 B | 80 × 8 bytes, binary-searched |
| Card effect data | `0x097DA800` | ~24 KB | ~887 × 28 bytes |
| Character sprites | `0x091F24DC` | ~377 KB | 29 duelists × 5 poses (64×64 4bpp) |
| Character palettes | `0x09250780` | ~14 KB | Palette data for sprites |
| Card pile bgs | `0x092515F4` | ~1.1 MB | 8 entries, 4bpp tiled backgrounds |
| Location thumbs | `0x09772E14` | ~394 KB | 3 periods × 26 locations |
| Effect context | `0x0201FD00` | IWRAM | Effect resolution state |
| Player duel data | `0x02022250` | EWRAM | 2 players × 0x2B08 bytes |

## String Table Format

Strings are stored as a **contiguous blob of null-terminated strings** followed by an **offset table** (uint32 LE offsets from the blob base).

```
[string 0]\0[string 1]\0...[string N-1]\0 | offset[0], offset[1], ..., offset[N]
```

The offset table has N+1 entries — the sentinel `offset[N]` marks the end of the last string.

Examples: `card_names_en` (at `0x08F25690`), `ui_en` (at `0x08E44760`).

## Card Stats Bitfield

At `0x08F243CC`, each card is a **single uint32**:

```
[31-29] Attr(3) | [28-25] Level(4) | [24-20] Type(5) | [19-18] Cat(2) | [17-9] ATK/10(9) | [8-0] DEF/10(9)
```

See [Card Data Structure](Card-Data-Structure) for full breakdown.

## Rendering Pipeline Notes

- Card pile backgrounds are **4bpp row-major nibble-packed** tiles, NOT bitplane-interleaved
- Screen entries use GBA bit 10 (H-flip) and bit 11 (V-flip); the encoder deduplicates across all 4 orientations
- `card_pile_background_load` (`0x080AD2B4`) is called twice by `render_duel_field_background` (`0x08085918`): first for the main background, second for a conditional overlay
- Character sprites are 64×64 pixels, stored as 4bpp tiles (2048 bytes per pose)
