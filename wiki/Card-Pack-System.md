# Card Pack System

The game features 49 different card packs that can be purchased in the shop. Each pack has its own cover art, description, and internal layout configuration.

## Data Structure

The card pack system is defined across several tables:

| Address | Category | Description |
|---------|----------|-------------|
| `0x0947EBB0` | Layouts | `CARD_PACK_LAYOUTS`: 49 matrix layouts (5632 bytes each) |
| `0x094C2274` | Palettes | `CARD_PACK_PALETTES`: 49 palettes (96 bytes each, 48 colors) |
| `0x094C34D4` | Bitmaps | `CARD_PACK_TILES`: 49 cover arts (3456 bytes each, 108 tiles) |
| `0x094EDD78` | Strings | `CARD_PACK_STRINGS`: Pack names and descriptions |

### Pack Covers (Bitmaps)

Each pack cover is an **8bpp raw bitmap** (1 byte per pixel) of size **64x88 pixels** (8x11 tiles).

The data is stored as linear tiles (64 bytes each). The ROM values are raw indices `0-47`, which the renderer maps to palette entries `160-208` by adding an offset of **160** to every non-zero pixel.

### Pack Layouts (Matrix)

The "Matrix" terminology in the code refers to the 8x11 tile grid that forms the portrait pack cover.

The primary renderer `render_card_pack_layout_type1` (0x080D1A40):
1. Iterates through the 88 tiles.
2. Applies the +160 palette shift.
3. Generates the 8bpp tile data in VRAM at `0x06005100`.
4. Builds the associated tilemap at `0x06001800`.


## Pack List (Partial)

| ID | Name | Description Snippet |
|----|------|-------------|
| 0 | Basic 1-A | I recommend this for one of your first purchases. |
| 1 | Basic 1-B | I recommend this for one of your first purchases. |
| ... | ... | ... |
| 36 | Effect Monsters | This pack has lots of Effect Monsters! |
| 39 | Various Fields | (Contains field spell related cards) |

## Key Functions

| Address | Name | Role |
|---------|------|------|
| `0x080D4EE4` | `render_card_pack_tiles` | Loads pack cover bitmap and palette |
| `0x080D1A40` | `render_card_pack_layout_type1` | Generates background from matrix layout |
| `0x080D78B8` | `render_card_pack_layout_type2` | Secondary layout renderer |
