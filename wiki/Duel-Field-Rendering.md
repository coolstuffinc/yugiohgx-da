# Duel Field Rendering

The game uses a matrix-based rendering system for the duel field backgrounds.

## Field Matrix Data

**Address**: `0x0947EBB0` · **Ghidra label**: `MATRIX_DATA`

This region contains tiled layout data for the duel field. It is organized into "sectors", each containing 2816 `uint16` entries. Each entry represents a tile or screen element.

## Rendering Pipeline

1. **`render_field_matrix_sector_type1`** (0x080D1A40):
   - Reads a sector from `MATRIX_DATA`.
   - Adds a tile offset (typically 160) to each entry.
   - Writes the resulting tilemap to VRAM (e.g., `0x06005100`).
   - Loads a associated palette (96 words per sector).
   - Renders a 11x8 grid of tiles to the front-buffer VRAM.

2. **`render_field_matrix_sector_type2`** (0x080D78B8):
   - Similar to Type 1, but used for different field types or layers.

## Implementation Details

The `uint16` entries in `MATRIX_DATA` are bit-packed:
- **Low Byte**: Tile index part 1.
- **High Byte**: Tile index part 2.
- If an entry is non-zero, it gets the 160 tile offset added, allowing for dynamic tile-base relocation.
