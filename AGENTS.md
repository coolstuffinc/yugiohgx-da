# yugiohgx-da — Agent Guidance

## Commands

```sh
uv sync                          # install deps (numpy, pillow)
uv run python3 -m unittest discover -s tests -v          # all unit tests
uv run python3 -m unittest tests.test_memory_ops -v      # single module
uv run python3 tests/test_rom_integration.py --rom /path/to/game.gba  # integration
uv run ygogxda <subcommand>     # CLI entrypoint
uv run python3 dumps/dump_sprites.py  # ad-hoc debug dumps
```

Env: `YGOGXDA_TEST_ROM` sets ROM path for integration tests. Tests also accept `--rom` arg.

There is no `setup.py` or `Makefile` — `pyproject.toml` drives everything via setuptools + uv.

## Project layout

- `src/ygogxda/cli.py` — CLI entrypoint (`main()`), registered as `ygogxda` script
- `src/ygogxda/rom.py` — `YugiohROM` class: memory region definitions + data accessors
- `src/ygogxda/memory.py` — `MemoryEmulator`: byte-level ROM read/write with real/virtual address translation
- `src/ygogxda/memory_ops.py` — high-level extract/patch operations wired to CLI
- `src/ygogxda/memory_map.py` — canonical path registry for `memory dump` and string table references
- `src/ygogxda/coverage.py` — `ROM_LAYOUT` list describing all known memory regions
- `tests/` — stdlib `unittest`, no pytest. Tests synthesize ROMs via `build_synthetic_rom()` helpers.
- `dumps/` — ad-hoc debug scripts (not part of the library)

Dead files: `src/main.py`, `src/testing.py` (empty), `src/japanese_encondings.py` (typo, unused).

## Memory addressing

GBA ROM is mapped at base address **0x08000000**. `MemoryEmulator` works with both:
- **Real addresses** (0x08000000-based) — used in `YugiohROM` region definitions
- **Virtual addresses** (0-based offsets into the raw file) — internal to `MemoryEmulator`

All `YugiohROM` region constants (e.g. `CARD_HIGH_RES_BITMAPS = slice(0x087CFACC, ...)`) use **real** addresses. The constructor reads from a `MemoryEmulator` that handles translation.

## BIG_3 Layer API (card pile backgrounds)

`YugiohROM` has these card pile background methods:

| Method | Returns | Description |
|---|---|---|
| `card_pile_background(index)` | `PIL.Image` | Composite image (all banks merged, 240×160) |
| `card_pile_backgrounds()` | generator of `PIL.Image` | All 8 composites |
| `card_pile_background_layers(index)` | `(layers_dict, pal_n, pal_payload)` | Per-bank images as `{bank: np.array}` (160×240, pixel values 0-15) |
| `encode_card_pile_background(layers, pal_n, pal_payload)` | `bytes` (static) | Re-encode layers into BIG_3 format |
| `patch_card_pile_background(index, layers)` | `None` | Encode and write layers back into the ROM in-place |

CLI:
```sh
ygogxda sprites extract card-pile --rom game.gba --index 0    # single entry
ygogxda sprites extract card-pile --rom game.gba               # all 8 entries
ygogxda sprites patch card-pile --rom game.gba --output patched.gba  # patch all from canonical dir
ygogxda sprites patch card-pile --rom game.gba --index 0 --layers-dir ./layers --output patched.gba
```

The encode uses flip-aware global tile dedup (checks all 4 orientations: original, H-flip, V-flip, HV-flip). The re-encoded data must fit within the original entry's slot — raises `ValueError` if it doesn't.

## Graphics encoding (GBA)

**8bpp tiled format** (card artworks, duelist sprites, token sprites):
- Data stored as `[tile_row][tile_col][px_row][px_col]` — reshape with `(tiles_high, tiles_wide, 8, 8)`, then `join_blocks((tiles_high, tiles_wide))` from `utils.py`
- Palette: 128 bytes = 64 × 16-bit little-endian GBA colors. Bit 15 is ignored by hardware. Use `image.putpalette(palette, rawmode="RGB;15")` for correct decoding.

**4bpp tiled format** (card pile backgrounds — BIG_3):
- Each tile is 32 bytes in standard GBA row-major nibble-packed format: 8 rows × 4 bytes per row. Each byte = 2 pixels (upper nibble = even/left column, lower nibble = odd/right column).
- Background data structure (reverse-engineered from `FUN_080ad2b4`):
  1. `u16[0]` = palette color count (`pal_n`); `u16[1..3]` = same value (redundant)
  2. Palette: bytes 8..8+pal_n*2 (GBA 15-bit little-endian colors). Color 0 of each 16-color bank is `0x7C1F` (magenta/transparent).
  3. Metadata at offset `pal_n*2 + 8`: `u16[0]` = tile count (`n_tiles`)
  4. Tile data at offset `pal_n*2 + 16`: `n_tiles` × 32 bytes (4bpp row-major nibble-packed)
  5. Screen entry pairs immediately following tile data: `u16[0]` = pair count, 6 bytes padding, then pairs of `[src_u16, dst_u16]`. src low 6 bits = dest position in 32-wide BG map (values 0-31 → charblock 0, 32-63 → charblock 1, subtract 32). dst = GBA screen entry format (bits 0-9 = tile idx, 10 = H-flip, 11 = V-flip, 12-15 = palette bank).
- Screen entries retain their original palette bank values (bits 12-15: 0, 1, or 2). The decoder must use per-entry bank selection: pixel value `n` in a tile at bank `b` maps to file color `b*16 + n`. Build a full 256-color palette from the file (pad unused entries with `0x7C1F`/magenta) and offset each tile's pixel values by `bank * 16` on the canvas.
- The underlying file palette has ~43 colors spanning 3 banks. Bank separators at indices 0, 16, 32 each start with `0x7C1F`.
- Rendered result: 240×160 pixels (30×20 tiles in a 32-wide map). Rely on `rom.card_pile_backgrounds()` or `rom.card_pile_background(index)` rather than manual decoding.

### Reverse-engineering notes (BIG_3 / FUN_080ad2b4)

The game function `FUN_080ad2b4` loads card pile backgrounds. Key observations:

**Palette layout (entry 0 example, 43 colors):**
| File index | GBA bank | Usage | Key colors |
|---|---|---|---|
| 0-15 | Bank 1 (PAL+32) | Card art background layer | Dark browns, blue-grays |
| 16-31 | Bank 2 (PAL+64) | Duel field/terrain layer | Warmer browns, tans, white |
| 32-42 | Bank 3 (PAL+96) | UI overlay frame | Grays, white |

Each bank starts with `0x7C1F` (magenta/transparent). Colors at indices 0-2 are identical across banks 1 and 2; indices 3-15 differ.

**How `FUN_080ad2b4` works:**
1. Reads `pal_n` from header, copies `pal_n` colors from the entry's palette data into GBA palette RAM at `PALETTE + param_4 * 32` (so file[0] lands at PALETTE[param_4*16], etc.)
2. Parses tile data and screen entry pairs
3. For each screen entry, sets bits 12-15 (palette bank) to `param_4` — this overrides whatever bank was originally in the file data
4. Writes tiles to VRAM charbase block(s)

However, the original screen entries in the ROM file have their own palette bank values (0, 1, 2). The game's override to `param_4` is a runtime thing — for decoding/editing, we use the original file-level bank values.

**Two render passes:** `render_duel_field_background` calls `FUN_080ad2b4` twice:
1. First: `param_4=1`, main entry data pointer (palette goes to GBA bank 1)
2. Second (conditional): `param_4=5`, different data pointer `puVar3` (unknown — possibly a shared/common overlay)

**Entry 7 anomaly:** Contains a standard sub-background (same format as entries 0-6) followed by ~1.6MB of extra data. Format of remaining data unknown — may be a pool of shared tiles or other resources.

**Tile dedup in original data:** The original 600 tile positions (30×20 visible area) reference only ~408 unique tiles. Many tiles are shared via H-flip/V-flip (bits 10-11 in dst). The encoder recreates this with flip-aware dedup.

**Common pitfalls:**
- Bitplane-interleaved 4bpp (used by some GBA tools) produces magenta "splattered" output (~31% pixel value 0). Always use row-major nibble-packed.
- Tile flip bits (H/V) are pre-applied when decoding to layer images. The encoder re-detects flips during dedup.
- Palette bank 0 in screen entries accesses GBA palette bank 0 (PAL+0..31), which may contain data loaded by a prior operation (e.g., main background). Not all 3 banks are purely from the BIG_3 entry.

**Sprite dimensions:**
| Resource | Size | Tiles | Palette colors |
|---|---|---|---|
| Card artwork | 80×80 | 10×10 | 64 |
| Duelist sprite | 64×64 | 8×8 | 64 |
| Location thumb | 96×64 | 12×8 | 64 |
| Token sprite | 80×80 | 10×10 | 64 |

## Known regions (coverage.py)

Tokens (BIG_2): `0x090A0610` — pointer table (14 entries), each entry = palette(0x80) + pixel_data(0x1900), stride 0x1980. Some entries share pointers.
Card pile BG / BIG_3: `0x092515F4` — 8 entries, 4bpp tiled, variable-sized, format described above.
Characters: `0x091F24DC` — bitmaps, `0x09250780` — palettes; 29 duelists × 5 pose variations.
Location thumbs: `0x09772E14` — pointer table with 3 periods × 26 locations.

## String tables

Architecture: contiguous string blob + offset table of uint32 LE. String region has `num_entries + 1` offsets — entry i spans `[offsets[i], offsets[i+1])`.

Canonical string tables (used by CLI): `card_names_en`, `card_names_jp` (encoding `japanese_rom`), `card_texts_en`, `ui_en`.

## Testing quirks

- `test_rom_integration.py` — mocks `_read_card_artworks` so it runs without ROM. Real ROM used if `YGOGXDA_TEST_ROM` is set.
- `test_memory_ops.py` — builds full synthetic ROMs with pointer tables, bitmap/palette data, and offsets. Covers sprite extract, patch round-trips, string bulk patching.
- Many tests mock `YugiohROM._read_card_artworks` because the artwork generator requires real ROM data (no synthetic fallback currently).
- `build_synthetic_rom()` in both test files must be kept in sync with any new `YugiohROM` regions added.

## Ghidra MCP

Configured in `opencode.json` — connects to `http://127.0.0.1:8080/`. Uses `ygogxda.gba` as the analyzed ROM.

## Code style

- No type annotations on most existing code. Prefer to match surrounding style.
- `PIL.Image.putpalette(rawmode="RGB;15")` handles GBA 15-bit color (bit 15 ignored) — do not manually mask.
- `numpy.reshape` order for tiled data: `(tiles_high, tiles_wide, 8, 8)`, then `join_blocks((tiles_high, tiles_wide))`.
