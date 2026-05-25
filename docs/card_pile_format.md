# Card Pile Background Format

Reverse-engineered from `FUN_080ad2b4` at `0x080ad2b4`. These are the deck-building /
card-selection UI backgrounds — 8 entries stored in the region `0x092515F4 .. 0x093F6DF0`.

## Data structure

```
offset 0:       u16[0..3] = pal_n         (4 redundant copies = 8 bytes)
offset 8:       palette                    (pal_n * 2 bytes, GBA 15-bit LE)
offset 8+pal_n*2:  u16     = tile_count
                   u8[6]   = padding (0x00)
                   tile_data              (tile_count * 32 bytes, 4bpp)
                   u16     = pair_count
                   u8[6]   = padding (0x00)
                   pairs                  (pair_count * 4 bytes)
```

## Tile format

Standard GBA **4bpp row-major nibble-packed** — NOT bitplane-interleaved.

- 8 rows × 4 bytes = 32 bytes per tile
- Each byte = 2 pixels: upper nibble = even/left column, lower nibble = odd/right column
- Bitplane-interleaved produces magenta "splattered" output (~31% pixel value 0)

Decode:
```python
for row in range(8):
    for col in range(8):
        byte = data[row * 4 + col // 2]
        pixel = byte >> 4 if col % 2 == 0 else byte & 0xF
```

## Screen entry pairs

`src` (u16, low 6 bits = col in 32-wide tilemap):
- Bits 0-4: column (0-31)
- Bit 5: charblock select (0 or 1; if 1, subtract 32 from column)
- Bits 8-15: row
- Position = col + row * 32

`dst` (u16, GBA screen entry format):
- Bits 0-9: tile index
- Bit 10: H-flip
- Bit 11: V-flip
- Bits 12-15: palette bank

## Palette layout

Each entry carries `pal_n` colors (~43 for entry 0). The file palette spans 3 banks:

| File index | GBA bank | Layer | Key colors |
|---|---|---|---|
| 0-15 | Bank 1 (PAL+32) | Card art background | Dark browns, blue-grays |
| 16-31 | Bank 2 (PAL+64) | Duel field/terrain | Warmer browns, tans, white |
| 32-42 | Bank 3 (PAL+96) | UI overlay frame | Grays, white |

Bank separators at indices 0, 16, 32 each start with `0x7C1F` (magenta/transparent).
Indices 0-2 are identical across banks 1 and 2; indices 3-15 differ.

## HOW `FUN_080ad2b4` works

1. Read `pal_n` from header
2. Copy `pal_n` colors from entry's palette to `PALETTE + param_4 * 32`
   (so file[0] lands at PALETTE[param_4*16], overlaps banks 1-3)
3. Parse tile data and screen entry pairs
4. For each screen entry, **override** bits 12-15 (palette bank) to `param_4`
5. Write tiles to VRAM charbase block(s)

The original file screen entries have their own bank values (0, 1, 2). The game's
override to `param_4` is a runtime convention — for decoding/editing we use the
original file-level bank values.

## Render passes

The caller `render_duel_field_background` calls `FUN_080ad2b4` **twice**:

1. **First**: `param_4=1`, pointer to the main entry data
2. **Second** (conditional): `param_4=5`, pointer `puVar3` — unknown data pointer,
   possibly a shared/common overlay or palette for something else

## Entry 7 anomaly

Entry 7 at `0x0926BFA0` contains a standard sub-background (same format as
entries 0-6) followed by ~1.6 MB of extra data. Format of the remaining data is
unknown — may be a pool of shared tiles or other resources.

## Tile dedup

The 600 tile positions (30 cols × 20 rows visible) reference only ~408 unique
tiles in the original data. Many tiles are shared via H-flip / V-flip
(bits 10-11 in dst). The encoder (`encode_card_pile_background`) recreates this
with flip-aware dedup checking all 4 orientations.

## Rendering result

240×160 pixels (30×20 tiles in a 32-wide map). Use `rom.card_pile_backgrounds()`
or `rom.card_pile_background(index)` for composite, or
`rom.card_pile_background_layers(index)` for per-bank layer images.
