from typing import Dict, List, Optional, Tuple, Any, Generator
import struct
from .memory import MemoryEmulator, mem_region
from .utils import charset_decode, sucessive_sub
from .gba import GBAHeader
from .passwords import YugiohPasswords
from .japanese_encoding import decode as japanese_decode
from .registry import (
    ASSETS,
    SpriteMetadata,
    SpriteCollection,
    ROMRegion,
    StringTableMetadata,
)
from PIL import Image
import numpy as np


class YugiohROM:
    # --- COMPATIBILITY CONSTANTS (Mapped from ASSETS registry) ---
    CARD_TOTAL_NUMBER = ASSETS.get_region("CARD_TOTAL_NUMBER").slice
    CARD_NUMBER_TO_ID = ASSETS.get_region("CARD_NUMBER_TO_ID").slice
    CARD_PASSWORD_KEYS = ASSETS.get_region("CARD_PASSWORD_KEYS").slice
    CARD_STATS = ASSETS.get_region("CARD_STATS").slice
    CARD_HIGH_RES_PALETTES = ASSETS.get_region("CARD_HIRES_PALETTES").slice
    CARD_HIGH_RES_BITMAPS = ASSETS.get_region("CARD_HIRES_BITMAPS").slice
    CHARACTERS_BITMAPS = ASSETS.get_region("CHAR_BITMAPS").slice
    CHARACTERS_PALETTES = ASSETS.get_region("CHAR_PALETTES").slice
    ACADEMY_LOCATIONS_THUMBS = ASSETS.get_region("LOC_THUMBNAILS").slice
    CARD_PILE_BG = ASSETS.get_region("CARD_PILE_BG").slice

    CARD_NAMES_EN = ASSETS.get_region("CARD_NAMES_EN").slice
    CARD_NAMES_OFFSETS_EN = ASSETS.get_region("CARD_NAMES_OFFSETS_EN").slice
    CARD_TEXTS_EN = ASSETS.get_region("CARD_TEXTS_EN").slice
    CARD_TEXTS_OFFSETS_EN = ASSETS.get_region("CARD_TEXTS_OFFSETS_EN").slice
    CARD_NAMES_JP = ASSETS.get_region("CARD_NAMES_JP").slice
    CARD_NAMES_OFFSETS_JP = ASSETS.get_region("CARD_NAMES_OFFSETS_JP").slice
    GAME_UI_STR_EN = ASSETS.get_region("GAME_UI_STR_EN").slice
    GAME_UI_OFFSETS_EN = ASSETS.get_region("GAME_UI_OFFSETS_EN").slice
    GAME_UI_OFF_EN = GAME_UI_OFFSETS_EN

    CARD_PACK_BITMAPS = ASSETS.get_region("CARD_PACK_BITMAPS").slice
    CARD_PACK_PALETTES = ASSETS.get_region("CARD_PACK_PALETTES").slice

    def __init__(self, filename: str, memory_map: bytes = None):
        payload = memory_map if memory_map is not None else filename
        self.rom = MemoryEmulator(payload)
        self.header = GBAHeader(self._read_header())
        self.num_cards = self.rom[self.CARD_TOTAL_NUMBER].read_integer(1)
        self._init_sprite_collections()
        self.card_names = self._read_all_strings("card_names_en")
        self.card_texts = self._read_all_strings("card_texts_en")
        self.card_names_jp = self._read_all_strings("card_names_jp")
        self.passwords = YugiohPasswords(
            self.rom[self.CARD_PASSWORD_KEYS].read_array(1201, dtype="I")
        )

    def _init_sprite_collections(self):
        self.collections: Dict[str, SpriteCollection] = {}
        for name, meta in ASSETS.sprites.items():
            getter = self._make_getter(name, meta)
            setter = self._make_setter(name, meta)
            self.collections[name] = SpriteCollection(
                resource=meta,
                getter=getter,
                setter=setter,
            )

    def _make_getter(self, name, meta: SpriteMetadata):
        BASE = 0x08000000

        def getter(rom: "YugiohROM", index: int, variation: int = 0):
            region = ASSETS.get_region(meta.bitmap_region or name)
            if meta.is_pointer_table:
                if meta.root_table_size > 0:
                    root_ptrs = rom.rom[region.slice].read_pointers(
                        meta.root_table_size
                    )
                    half = meta.root_table_size // 2
                    v = variation if meta.variations > 1 else 0
                    bmp_table_ptr = root_ptrs[v]
                    bmp_ptrs = rom.rom.read_pointers(meta.count, offset=bmp_table_ptr)
                    size = meta.entry_stride or (
                        meta.width * meta.height * meta.bpp // 8
                    )
                    bitmap_data = rom.rom.read_bytes(
                        size, offset=bmp_ptrs[index] + meta.bitmap_header_skip
                    )
                    pal_data = b""
                    if meta.palette_region:
                        pal_table_ptr = root_ptrs[half + v]
                        pal_ptrs = rom.rom.read_pointers(
                            meta.count, offset=pal_table_ptr
                        )
                        pal_size = meta.palette_stride or (meta.palette_colors * 2)
                        pal_data = rom.rom.read_bytes(pal_size, offset=pal_ptrs[index])
                    return bytes(bitmap_data), bytes(pal_data)
                ptr = 0
                if meta.pointers_are_packed:
                    n = meta.count * meta.variations
                    raw = rom.rom[region.slice].read_pointers(n)
                    all_ptrs = [raw] if isinstance(raw, int) else raw
                    ptr = all_ptrs[index * meta.variations + variation]
                else:
                    raw_ptrs = rom.rom[region.slice].read_pointers(index + 1)
                    ptrs = [raw_ptrs] if isinstance(raw_ptrs, int) else raw_ptrs
                    ptr = ptrs[index]
                    if meta.variations > 1:
                        raw_var_ptrs = rom.rom.read_pointers(
                            meta.variations, offset=ptr
                        )
                        var_ptrs = (
                            [raw_var_ptrs]
                            if isinstance(raw_var_ptrs, int)
                            else raw_var_ptrs
                        )
                        if var_ptrs[0] >= BASE:
                            ptr = var_ptrs[variation]
                size = meta.entry_stride or (meta.width * meta.height * meta.bpp // 8)
                bitmap_data = (
                    rom.rom.read_bytes(size, offset=ptr) if ptr else b"\x00" * size
                )

                pal_data = b""
                if meta.palette_region:
                    pal_reg = ASSETS.get_region(meta.palette_region)
                    if meta.palette_stride == 0:
                        raw_pal_ptrs = rom.rom[pal_reg.slice].read_pointers(index + 1)
                        pal_ptrs = (
                            [raw_pal_ptrs]
                            if isinstance(raw_pal_ptrs, int)
                            else raw_pal_ptrs
                        )
                        pal_ptr = pal_ptrs[index]
                        pal_data = (
                            rom.rom.read_bytes(128, offset=pal_ptr)
                            if pal_ptr
                            else b"\x00" * 128
                        )
                    else:
                        pal_data = rom.rom.read_bytes(
                            meta.palette_stride,
                            offset=pal_reg.start + index * meta.palette_stride,
                        )
                return bytes(bitmap_data), bytes(pal_data)
            else:
                start = region.start + index * meta.entry_stride
                bitmap_data = rom.rom.read_bytes(meta.entry_stride, offset=start)
                pal_data = b""
                if meta.palette_region:
                    pal_reg = ASSETS.get_region(meta.palette_region)
                    pal_data = rom.rom.read_bytes(
                        meta.palette_stride,
                        offset=pal_reg.start + index * meta.palette_stride,
                    )
                return bytes(bitmap_data), bytes(pal_data)

        return getter

    def _make_setter(self, name, meta: SpriteMetadata):
        def setter(
            rom: "YugiohROM", index: int, bmp: bytes, pal: bytes, variation: int = 0
        ):
            region = ASSETS.get_region(meta.bitmap_region or name)
            if meta.is_pointer_table:
                if meta.root_table_size > 0:
                    root_ptrs = rom.rom[region.slice].read_pointers(
                        meta.root_table_size
                    )
                    half = meta.root_table_size // 2
                    v = variation if meta.variations > 1 else 0
                    bmp_table_ptr = root_ptrs[v]
                    bmp_ptrs = rom.rom.read_pointers(meta.count, offset=bmp_table_ptr)
                    rom.rom[
                        mem_region(bmp_ptrs[index] + meta.bitmap_header_skip, len(bmp))
                    ] = bmp
                    if meta.palette_region:
                        pal_table_ptr = root_ptrs[half + v]
                        pal_ptrs = rom.rom.read_pointers(
                            meta.count, offset=pal_table_ptr
                        )
                        rom.rom[mem_region(pal_ptrs[index], len(pal))] = pal
                    return
                if meta.pointers_are_packed:
                    n = meta.count * meta.variations
                    raw = rom.rom[region.slice].read_pointers(n)
                    all_ptrs = [raw] if isinstance(raw, int) else raw
                    ptr = all_ptrs[index * meta.variations + variation]
                    if ptr:
                        rom.rom[mem_region(ptr, len(bmp))] = bmp
                    if meta.palette_region:
                        pal_reg = ASSETS.get_region(meta.palette_region)
                        if meta.palette_stride == 0:
                            raw_pal = rom.rom[pal_reg.slice].read_pointers(index + 1)
                            all_pal_ptrs = (
                                [raw_pal] if isinstance(raw_pal, int) else raw_pal
                            )
                            pal_ptr = all_pal_ptrs[index]
                            if pal_ptr:
                                rom.rom[mem_region(pal_ptr, len(pal))] = pal
                        else:
                            rom.rom[
                                mem_region(
                                    pal_reg.start
                                    + index * (meta.palette_stride or 128),
                                    len(pal),
                                )
                            ] = pal
                else:
                    raw_ptrs = rom.rom[region.slice].read_pointers(index + 1)
                    ptrs = [raw_ptrs] if isinstance(raw_ptrs, int) else raw_ptrs
                    ptr = ptrs[index]
                    if meta.variations > 1:
                        raw_var_ptrs = rom.rom.read_pointers(
                            meta.variations, offset=ptr
                        )
                        var_ptrs = (
                            [raw_var_ptrs]
                            if isinstance(raw_var_ptrs, int)
                            else raw_var_ptrs
                        )
                        ptr = var_ptrs[variation]
                    if ptr:
                        rom.rom[mem_region(ptr, len(bmp))] = bmp
                    if meta.palette_region:
                        pal_reg = ASSETS.get_region(meta.palette_region)
                        if meta.palette_stride == 0:
                            raw_pal_ptrs = rom.rom[pal_reg.slice].read_pointers(
                                index + 1
                            )
                            pal_ptrs = (
                                [raw_pal_ptrs]
                                if isinstance(raw_pal_ptrs, int)
                                else raw_pal_ptrs
                            )
                            pal_ptr = pal_ptrs[index]
                            if pal_ptr:
                                rom.rom[mem_region(pal_ptr, len(pal))] = pal
                        else:
                            rom.rom[
                                mem_region(
                                    pal_reg.start
                                    + index * (meta.palette_stride or 128),
                                    len(pal),
                                )
                            ] = pal
            else:
                rom.rom[
                    mem_region(region.start + index * meta.entry_stride, len(bmp))
                ] = bmp
                if meta.palette_region:
                    pal_reg = ASSETS.get_region(meta.palette_region)
                    rom.rom[
                        mem_region(
                            pal_reg.start + index * meta.palette_stride, len(pal)
                        )
                    ] = pal

        return setter

    def get_sprite(
        self, resource_name: str, index: int, variation: int = 0
    ) -> Image.Image:
        return self.collections[resource_name].get(self, index, variation)

    def patch_sprite(
        self, resource_name: str, index: int, image: Image.Image, variation: int = 0
    ):
        self.collections[resource_name].patch(self, index, image, variation)

    def get_string_table(self, table_name: str) -> List[str]:
        return self._read_all_strings(table_name)

    def _read_all_strings(self, table_name):
        meta = ASSETS.string_tables[table_name.lower()]
        region = ASSETS.get_region(meta.strings_region)
        off_region = ASSETS.get_region(meta.offsets_region)
        mem_strings = self.rom[region.slice]
        mem_offsets = self.rom[off_region.slice]
        elements = len(mem_offsets) // 4
        offsets = mem_offsets.read_array(elements, dtype="I")
        sizes = sucessive_sub(offsets)

        def decode(raw):
            if meta.encoding == "japanese_rom":
                return japanese_decode(raw)
            return charset_decode(raw)

        return [
            decode(mem_strings.read_struct(f"<{s}s", offset=o))
            for o, s in zip(offsets, sizes)
        ]

    def save(self, filename: str):
        self.rom.write(filename)

    @property
    def game_title(self) -> str:
        return charset_decode(self.header.game_title)

    @property
    def game_code(self) -> str:
        return charset_decode(self.header.game_code)

    def _read_header(self) -> bytes:
        return self.rom.read_struct(GBAHeader.STRUCT_FMT)

    # --- Legacy properties (for backward compatibility) ---
    @property
    def CARD_STATS(self):
        return ASSETS.get_region("CARD_STATS").slice

    @property
    def CARD_NUMBER_TO_ID(self):
        return ASSETS.get_region("CARD_NUMBER_TO_ID").slice

    @property
    def CARD_PASSWORD_KEYS(self):
        return ASSETS.get_region("CARD_PASSWORD_KEYS").slice

    @property
    def CARD_HIRES_BITMAPS(self):
        return ASSETS.get_region("CARD_HIRES_BITMAPS").slice

    @property
    def CARD_HIRES_PALETTES(self):
        return ASSETS.get_region("CARD_HIRES_PALETTES").slice

    @property
    def CARD_NAMES_EN(self):
        return ASSETS.get_region("CARD_NAMES_EN").slice

    @property
    def CARD_NAMES_OFFSETS_EN(self):
        return ASSETS.get_region("CARD_NAMES_OFFSETS_EN").slice

    @property
    def CARD_TEXTS_EN(self):
        return ASSETS.get_region("CARD_TEXTS_EN").slice

    @property
    def CARD_TEXTS_OFFSETS_EN(self):
        return ASSETS.get_region("CARD_TEXTS_OFFSETS_EN").slice

    @property
    def GAME_UI_STR_EN(self):
        return ASSETS.get_region("GAME_UI_STR_EN").slice

    @property
    def GAME_UI_OFFSETS_EN(self):
        return ASSETS.get_region("GAME_UI_OFFSETS_EN").slice

    @property
    def CARD_NAMES_JP(self):
        return ASSETS.get_region("CARD_NAMES_JP").slice

    @property
    def CARD_NAMES_OFFSETS_JP(self):
        return ASSETS.get_region("CARD_NAMES_OFFSETS_JP").slice

    @property
    def CARD_TOTAL_NUMBER(self):
        return ASSETS.get_region("CARD_TOTAL_NUMBER").slice

    @property
    def CARD_PILE_BG(self):
        return ASSETS.get_region("CARD_PILE_BG").slice

    # --- Compatibility generators ---
    def card_images(self):
        for i in range(self.num_cards):
            yield self.get_sprite("card", i)

    def duelist_sprites(self):
        for i in range(29):
            yield [self.get_sprite("duelist", i, v) for v in range(5)]

    def location_thumbs(self):
        for v in range(3):
            yield [self.get_sprite("location-thumb", i, v) for i in range(26)]

    # --- Card pile backgrounds ---
    def card_pile_background(self, index):
        p_entries = self.rom[self.CARD_PILE_BG].read_pointers(8)
        return self._decode_card_pile(p_entries[index])

    def _parse_card_pile_entry(self, p_entry):
        data = self.rom.read_bytes(32 * 450 + 8 + 2000, offset=p_entry)
        pal_n = data[0] | (data[1] << 8)
        pal_payload = data[8 : 8 + pal_n * 2]
        meta_off = pal_n * 2 + 8
        tile_count = data[meta_off] | (data[meta_off + 1] << 8)
        tile_off = meta_off + 8
        tile_data = data[tile_off : tile_off + tile_count * 32]
        return data, pal_n, pal_payload, tile_count, tile_off, tile_data

    def _decode_card_pile(self, p_entry):
        data, pal_n, pal_payload, tile_count, tile_off, tile_data = (
            self._parse_card_pile_entry(p_entry)
        )
        tiles = np.zeros((tile_count, 8, 8), dtype=np.uint8)
        for ti in range(tile_count):
            tbase = ti * 32
            for py in range(8):
                for col in range(8):
                    bi = tbase + py * 4 + col // 2
                    b = tile_data[bi]
                    tiles[ti, py, col] = b >> 4 if col % 2 == 0 else b & 0xF
        screen_off = tile_off + tile_count * 32
        num_pairs = data[screen_off] | (data[screen_off + 1] << 8)
        pair_data = data[screen_off + 8 : screen_off + 8 + num_pairs * 4]
        screen_map = {}
        for i in range(num_pairs):
            src, dst = struct.unpack_from("<HH", pair_data, i * 4)
            src_tile = src & 0x3F
            if src_tile > 31:
                src_tile -= 32
            position = src_tile | ((src & 0xFF00) >> 3)
            screen_map[position] = dst
        if not screen_map:
            return None
        max_pos = max(screen_map.keys())
        map_w, map_h = 32, (max_pos // 32) + 1
        canvas = np.zeros((map_h * 8, map_w * 8), dtype=np.uint8)
        for pos, dst in screen_map.items():
            ty, tx = pos // 32, pos % 32
            dst_tile, hf, vf, bank = (
                dst & 0x3FF,
                (dst >> 10) & 1,
                (dst >> 11) & 1,
                (dst >> 12) & 0xF,
            )
            if dst_tile < tile_count:
                tile = tiles[dst_tile].copy()
                if hf:
                    tile = np.fliplr(tile)
                if vf:
                    tile = np.flipud(tile)
                canvas[ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8] = tile + bank * 16
        rows, cols = np.any(canvas != 0, axis=1), np.any(canvas != 0, axis=0)
        if not rows.any():
            return None
        y0, y1 = np.where(rows)[0][[0, -1]]
        x0, x1 = np.where(cols)[0][[0, -1]]
        y0, x0 = (y0 // 8) * 8, (x0 // 8) * 8
        y1, x1 = (y1 // 8 + 1) * 8, (x1 // 8 + 1) * 8
        canvas = canvas[y0:y1, x0:x1]
        palette = bytearray()
        for j in range(256):
            v = struct.unpack_from("<H", pal_payload, j * 2)[0] if j < pal_n else 0x7C1F
            palette.extend([v & 0xFF, (v >> 8) & 0xFF])
        image = Image.fromarray(canvas)
        image.putpalette(palette, rawmode="RGB;15")
        return image

    def card_pile_background_layers(self, index):
        p_entries = self.rom[self.CARD_PILE_BG].read_pointers(8)
        data, pal_n, pal_payload, tile_count, tile_off, tile_data = (
            self._parse_card_pile_entry(p_entries[index])
        )
        tiles = np.zeros((tile_count, 8, 8), dtype=np.uint8)
        for ti in range(tile_count):
            tbase = ti * 32
            for py in range(8):
                for col in range(8):
                    bi = tbase + py * 4 + col // 2
                    b = tile_data[bi]
                    tiles[ti, py, col] = b >> 4 if col % 2 == 0 else b & 0xF
        screen_off = tile_off + tile_count * 32
        num_pairs = data[screen_off] | (data[screen_off + 1] << 8)
        pair_data = data[screen_off + 8 : screen_off + 8 + num_pairs * 4]
        layers = {}
        for i in range(num_pairs):
            src, dst = struct.unpack_from("<HH", pair_data, i * 4)
            src_tile = src & 0x3F
            if src_tile > 31:
                src_tile -= 32
            position = src_tile | ((src & 0xFF00) >> 3)
            dst_tile, hf, vf, bank = (
                dst & 0x3FF,
                (dst >> 10) & 1,
                (dst >> 11) & 1,
                (dst >> 12) & 0xF,
            )
            if dst_tile >= tile_count:
                continue
            tile = tiles[dst_tile].copy()
            if hf:
                tile = np.fliplr(tile)
            if vf:
                tile = np.flipud(tile)
            ty, tx = position // 32, position % 32
            if bank not in layers:
                layers[bank] = np.zeros((20 * 8, 32 * 8), dtype=np.uint8)
            layers[bank][ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8] = tile
        for bank in layers:
            layers[bank] = layers[bank][:, :240]
        return layers, pal_n, pal_payload

    def patch_card_pile_background(self, index, layers):
        pass

    def card_artwork_bitmap(self, card_id):
        return self.rom[self.CARD_HIGH_RES_BITMAPS.start + 6400 * card_id, 6400]

    def card_artwork_palette(self, card_id):
        return self.rom[self.CARD_HIGH_RES_PALETTES.start + 128 * card_id, 128]

    def _read_card_artworks(self):
        return iter(())  # For testing
