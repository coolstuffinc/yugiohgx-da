import numpy as np
from PIL import Image
from .utils import join_blocks


class GBAGraphics:
    """Universal helper for GBA tiled graphics.

    Palette handling uses PIL's native rawmode='RGB;15' for correct 5-bit expansion.
    """

    @staticmethod
    def decode_4bpp_tiles(data):
        """Decode raw bytes into a list of 8x8 tiles (4bpp, row-major nibble-packed)."""
        tile_count = len(data) // 32
        tiles = np.zeros((tile_count, 8, 8), dtype=np.uint8)
        for ti in range(tile_count):
            tbase = ti * 32
            for py in range(8):
                for cp in range(4):
                    b = data[tbase + py * 4 + cp]
                    tiles[ti, py, cp * 2] = b & 0x0F
                    tiles[ti, py, cp * 2 + 1] = b >> 4
        return tiles

    @staticmethod
    def decode_8bpp_tiles(data):
        """Decode raw bytes into a list of 8x8 tiles (8bpp)."""
        tile_count = len(data) // 64
        return np.frombuffer(data, dtype=np.uint8).copy().reshape(tile_count, 8, 8)

    @staticmethod
    def encode_4bpp_tiles(tiles):
        """Encode 8x8 tiles into raw nibble-packed bytes (4bpp)."""
        tile_count = tiles.shape[0]
        data = bytearray(tile_count * 32)
        for ti in range(tile_count):
            tbase = ti * 32
            for py in range(8):
                for cp in range(4):
                    p1 = tiles[ti, py, cp * 2] & 0x0F
                    p2 = tiles[ti, py, cp * 2 + 1] & 0x0F
                    data[tbase + py * 4 + cp] = p1 | (p2 << 4)
        return bytes(data)

    @staticmethod
    def encode_8bpp_tiles(tiles):
        """Encode 8x8 tiles into raw bytes (8bpp)."""
        return tiles.flatten().tobytes()

    @staticmethod
    def assemble_from_map(tiles, tile_map):
        """Assemble an image from tiles using a 2D array of tile indices."""
        h_tiles, w_tiles = tile_map.shape
        canvas = np.zeros((h_tiles * 8, w_tiles * 8), dtype=np.uint8)
        for r in range(h_tiles):
            for c in range(w_tiles):
                idx = tile_map[r, c]
                if idx < len(tiles):
                    canvas[r * 8 : (r + 1) * 8, c * 8 : (c + 1) * 8] = tiles[idx]
        return canvas

    @staticmethod
    def gba_palette_to_rgb(pal_bytes):
        """Convert GBA BGR555 palette bytes to flat RGB list (padded to 256 colors).
        Only needed if you need raw RGB values outside PIL.
        """
        palette = []
        for i in range(len(pal_bytes) // 2):
            v = pal_bytes[i * 2] | (pal_bytes[i * 2 + 1] << 8)
            r = ((v >> 0) & 0x1F) * 255 // 31
            g = ((v >> 5) & 0x1F) * 255 // 31
            b = ((v >> 10) & 0x1F) * 255 // 31
            palette.extend([r, g, b])
        palette.extend([255, 0, 255] * (256 - (len(palette) // 3)))
        return palette

    @classmethod
    def create_image(cls, canvas, palette_bytes, bank_index=None):
        """Create a PIL P-mode image from a pixel canvas and GBA palette.

        Uses PIL's native rawmode='RGB;15' for correct 5-bit expansion,
        matching the original YugiohROM extraction exactly.

        bank_index: if set, select a 16-color bank (32 bytes) from a multi-bank palette.
        """
        img = Image.fromarray(canvas, mode="P")
        if bank_index is not None:
            start = bank_index * 32
            img.putpalette(palette_bytes[start : start + 32], rawmode="RGB;15")
        else:
            img.putpalette(palette_bytes, rawmode="RGB;15")
        return img


class YugiohGraphics:
    def __init__(self, bitmaps, palettes, num_cards=1201):
        self.bitmaps = bitmaps
        self.palettes = palettes
        self.num_cards = num_cards

    def artworks(self):
        tiles = GBAGraphics.decode_8bpp_tiles(self.bitmaps)
        for i in range(self.num_cards):
            icon_tiles = tiles[i * 100 : (i + 1) * 100]
            canvas = join_blocks(icon_tiles.reshape(10, 10, 8, 8), (10, 10))
            palette = self.palettes[i * 128 : (i + 1) * 128]
            yield GBAGraphics.create_image(canvas, palette)
