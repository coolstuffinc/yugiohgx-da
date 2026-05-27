from .memory import *
from .utils import *
from .gba import GBAHeader
from .passwords import YugiohPasswords
from .japanese_encoding import decode as japanese_decode
from .graphics import GBAGraphics
from PIL import Image
import numpy as np


class YugiohROM:
    # Memory Mapping
    CARD_TOTAL_NUMBER = mem_region(0x087A8620, 4)  # A integer with value 1200
    # Graphics
    CARD_HIGH_RES_PALETTES = mem_region(
        0x087AA24C, 1201 * 128
    )  # 128  B each card palette
    CARD_HIGH_RES_BITMAPS = mem_region(
        0x087CFACC, 1201 * 6400
    )  #  64 KB each card bitmap
    ACADEMY_LOCATIONS_THUMBS = slice(0x09772E14, 0x097D549F)
    CHARACTERS_BITMAPS = slice(0x091F24DC, 0x09250780)
    CHARACTERS_PALETTES = slice(0x09250780, 0x092515F4)
    DUEL_FIELD_BG = slice(0x092515F4, 0x093F6DF0)
    # English
    # - string section
    CARD_NAMES_EN = slice(0x08F25690, 0x08F2A68B)  # 0x00, 0x00, Blue...
    CARD_TEXTS_EN = slice(0x08F2B950, 0x08F58293)  # 0x00, 0x00, This lege...
    CARD_SHOP_PACK_INFO_EN = slice(0x094EDD78, 0x094EEF57)  # Basic 1-A, I recom ...
    TUTORIAL_DIALOGUES_EN = slice(0x09472826, 0x0947EBA0)  # On the duel screen, ...
    GAME_UI_STRINGS_EN = slice(0x093F6DF0, 0x094280A0)
    # - offsets
    CARD_NAMES_OFFSETS_EN = mem_region(0x08F2A68C, 1201 * 4)  # 1201 ints (4 Bytes each)
    CARD_TEXTS_OFFSETS_EN = mem_region(0x08F58294, 1201 * 4)  #
    GAME_UI_OFFSETS_EN = mem_region(0x094280B0, 4524 * 4)  #
    # - pointers
    TUTORIAL_INSTRUCT_EN = mem_region(0x097FD78C, 68 * 4)  # 68 Pointers to Strings
    TUTORIAL_SECTIONS_EN = mem_region(0x097FD78C, 11 * 4)  # 11 Pointers to Strings
    CHARS_FULL_NAMES_EN = mem_region(0x097F0BC8, 36 * 4)  # 36 Pointers to Strings
    CHARS_SHORT_NAMES_EN = mem_region(0x097F0C58, 36 * 4)  # 36 Pointers to Strings
    DUELIST_TITLES_EN = mem_region(0x097F0D50, 14 * 4)  # 14 ..
    ACADEMY_DORMS_EN = mem_region(0x097F0D88, 3 * 4)  #  3 ..
    CARD_MONSTER_TYPES_EN = mem_region(0x097D7B38, 24 * 4)  # 24 ..
    CARD_MONSTER_ATTRS_EN = mem_region(0x097D7B9C, 7 * 4)  #  7 ..
    CARD_TYPES_EN = mem_region(0x097D7BB8, 7 * 4)  #  7 ..
    ACADEMY_LOCATIONS_NAMES_EN = mem_region(
        0x097F0CE8, 26 * 4
    )  # 26 Pointers to Strings
    # Japanese
    # - string section
    CARD_NAMES_JP = slice(0x08F5B180, 0x08F61183)  # 0x00, 0x00, ブルーアイズ...
    CARD_TEXTS_JP = slice(0)
    # - offsets
    CARD_NAMES_OFFSETS_JP = mem_region(0x08F59EBC, 1201 * 4)  # 1201 ints (4 Bytes each)
    CARD_TEXTS_OFFSETS_JP = slice(0)
    # - structs
    EVENT_NAMES_JP = mem_region(0x0942C760, 71 * 516)  # 71 Structured Data
    # - pointers
    OPPONENT_NAMES_JP = mem_region(0x097F468C, 36 * 4)  # 36 Pointers to Strings
    EXAM_TYPE_JP = mem_region(0x097F471C, 7 * 4)  #  7 Pointers to Strings
    # DATA
    #
    CARD_TOKEN_INFO = slice(0x090A0540, 0x090A0610)
    TOKEN_SPRITES = mem_region(0x090A0610, 14 * 4)  # 14 ptrs to token sprites
    # Card Stats
    CARD_STATS = mem_region(
        0x08F243CC, 1201 * 4
    )  # 1201 uint32: bit-packed attr|level|type|ATK|DEF
    # LUT
    # - Ordinal number to id
    CARD_NUMBER_TO_ID = mem_region(0x087A8624, 1201 * 2)  # 1201 words (2 Bytes)
    # - Event to related Player ID
    EVENT_TO_PLAYER_ID = mem_region(0x0942C760, 150 * 2)
    # - Card password keys
    CARD_PASSWORD_KEYS = mem_region(0x087A8F88, 1201 * 4)  # 1201 ints (4 Bytes)
    # MISC strings
    LICENSED_BY_1 = mem_region(0x0946C5F0, 21)
    LICENSED_BY_2 = mem_region(0x097D5F24, 21)

    def __init__(self, filename, memory_map=None):
        payload = memory_map if memory_map is not None else filename
        self.rom = MemoryEmulator(payload)
        self.header = GBAHeader(self._read_header())
        self.num_cards = self._read_card_total_number()  # This is used afterwards
        self.card_names = self._read_card_names()
        self.card_texts = self._read_card_texts()
        self.card_names_jp = self._read_card_names_jp()
        self.card_images = self._read_card_artworks()
        # self.card_thumbs = self._read_card_thumbnails()
        self.passwords = YugiohPasswords(self._read_card_password_keys())
        card_number_id = self._read_card_number_to_id()

    @property
    def game_title(self):
        """Returns the Game Title YUGIOHGXDA"""
        return charset_decode(self.header.game_title)

    @property
    def rom_entry_point(self):
        return hex(self.header.rom_entry_point)

    @property
    def game_code(self):
        return charset_decode(self.header.game_code)

    def patch(self, patched: MemoryEmulator):
        """Update a memory region with new contents"""
        self.rom[patched.region] = patched._payload

    def save(self, filename):
        """Write modified rom data to a file"""
        self.rom.write(filename)

    def card_image(self, card_id):
        """Returns memory region for a card artwork"""
        return self.card_artwork_bitmap(card_id)

    def card_artwork_bitmap(self, card_id):
        num_cards = (
            YugiohROM.CARD_HIGH_RES_BITMAPS.stop - YugiohROM.CARD_HIGH_RES_BITMAPS.start
        ) // 6400
        if card_id < 0 or card_id >= num_cards:
            raise IndexError(f"card_id must be between 0 and {num_cards - 1}")

        start = YugiohROM.CARD_HIGH_RES_BITMAPS.start + 6400 * card_id
        return self.rom[start, 6400]

    def card_artwork_palette(self, card_id):
        num_cards = (
            YugiohROM.CARD_HIGH_RES_PALETTES.stop
            - YugiohROM.CARD_HIGH_RES_PALETTES.start
        ) // 128
        if card_id < 0 or card_id >= num_cards:
            raise IndexError(f"card_id must be between 0 and {num_cards - 1}")

        start = YugiohROM.CARD_HIGH_RES_PALETTES.start + 128 * card_id
        return self.rom[start, 128]

    def card_text(self, card_id):
        """Returns memory region for a card text"""
        offsets = YugiohROM.CARD_TEXTS_OFFSETS_EN
        strings = YugiohROM.CARD_TEXTS_EN
        card_text = self._read_string_with_offset(card_id, strings, offsets)
        return card_text

    def card_name(self, card_id):
        """Returns memory region for a card name"""
        offsets = YugiohROM.CARD_NAMES_OFFSETS_EN
        strings = YugiohROM.CARD_NAMES_EN
        card_name = self._read_string_with_offset(card_id, strings, offsets)
        return card_name

    def _read_string_with_offset(
        self, string_id, string_region, offset_region, offset_size=4
    ):
        """Read one string from memory region given a offset table"""
        mem_offsets = self.rom[offset_region]
        elements = len(mem_offsets) // offset_size
        # This assumes that each offset is 4 bytes long
        offsets = mem_offsets.read_array(elements, dtype="I")
        string_base = int(string_region.start)
        string_start = string_base + int(offsets[string_id])
        string_stop = string_base + int(offsets[string_id + 1]) - 1
        memory = self.rom[string_start:string_stop]
        return memory

    def _read_all_strings(
        self, string_region, offset_region, offset_size=4, decoder=charset_decode
    ):
        """Returns a list with all strings given a offset table"""
        mem_strings = self.rom[string_region]
        mem_offsets = self.rom[offset_region]
        elements = len(mem_offsets) // offset_size
        # This assumes that each offset is 4 bytes long
        offsets = mem_offsets.read_array(elements, dtype="I")
        sizes = sucessive_sub(offsets)

        strings = []
        for offset, size in zip(offsets, sizes):
            data = mem_strings.read_struct(f"<{size}s", offset=offset)
            string = decoder(data)
            strings.append(string)
        return strings

    def _read_header(self):
        """Returns the struct payload with header info"""
        data = self.rom.read_struct(GBAHeader.STRUCT_FMT)
        return data

    def _read_card_number_to_id(self):
        """Returns a LUT to convert card number to id"""
        LUT = self.rom[YugiohROM.CARD_NUMBER_TO_ID]
        return LUT.read_array(1201, dtype="H")

    def _read_card_password_keys(self):
        """Returns password decryption keys"""
        keys = self.rom[YugiohROM.CARD_PASSWORD_KEYS]
        return keys.read_array(1201, dtype="I")

    def _read_card_total_number(self):
        """Returns 1200"""
        num_cards = self.rom[YugiohROM.CARD_TOTAL_NUMBER]
        return num_cards.read_integer(1)

    def _read_card_names(self):
        """Returns a list with the english card names"""
        strings = YugiohROM.CARD_NAMES_EN
        offsets = YugiohROM.CARD_NAMES_OFFSETS_EN
        return self._read_all_strings(strings, offsets)

    def _read_card_names_jp(self):
        """Returns a list with the japanese card names"""
        strings = YugiohROM.CARD_NAMES_JP
        offsets = YugiohROM.CARD_NAMES_OFFSETS_JP
        return self._read_all_strings(strings, offsets, decoder=japanese_decode)

    def _read_card_texts(self):
        """Returns a list with all english card texts"""
        strings = YugiohROM.CARD_TEXTS_EN
        offsets = YugiohROM.CARD_TEXTS_OFFSETS_EN
        return self._read_all_strings(strings, offsets)

    def _read_hi_card_palettes(self):
        """Reads palettes for 80x80px card artworks: 8bpp"""
        palettes = self.rom[YugiohROM.CARD_HIGH_RES_PALETTES]
        shape = (1201, 128)
        data = palettes.read_array(shape, dtype="B")  # words
        return data

    def _read_hi_card_bitmaps(self):
        """Reads bitmaps for 80x80px card artworks"""
        bitmaps = self.rom[YugiohROM.CARD_HIGH_RES_BITMAPS]
        shape = (1201, 80 * 80)
        data = bitmaps.read_array(shape, dtype="B")  # words
        return data

    def _read_card_artworks(self):
        """Returns a generator with artwork for each card using GBAGraphics"""
        hires_bmp = self._read_hi_card_bitmaps()
        hires_pal = self._read_hi_card_palettes()
        tiles = hires_bmp.reshape(-1, 8, 8)
        for idx in range(self.num_cards):
            icon_tiles = tiles[idx * 100 : (idx + 1) * 100]
            canvas = join_blocks(icon_tiles.reshape(10, 10, 8, 8), (10, 10))
            palette = hires_pal[idx]
            yield GBAGraphics.create_image(canvas, palette)

    def _read_lo_card_palettes(self):
        """Reads palettes for low res card artworks"""
        raise NotImplementedError
        return

    def _read_lo_card_bitmaps(self):
        """Reads bitmaps for low res card artworks"""
        raise NotImplementedError
        return

    def _read_card_thumbnails(self):
        """Returns a generator with thumbnails for each card"""
        raise NotImplementedError
        return

    def duelist_sprites(self):
        mem_bitmaps = self.rom[YugiohROM.CHARACTERS_BITMAPS]
        mem_palettes = self.rom[YugiohROM.CHARACTERS_PALETTES]
        p_duelist_bitmaps = mem_bitmaps.read_pointers(29)
        p_duelist_palette = mem_palettes.read_pointers(29)

        for p_duelist, p_palette in zip(p_duelist_bitmaps, p_duelist_palette):
            palette = self.rom.read_array(128, offset=p_palette)
            p_variations = self.rom.read_pointers(5, offset=p_duelist)
            images = []
            for p_bitmap in p_variations:
                data = self.rom.read_bytes(4096, offset=p_bitmap)
                tiles = GBAGraphics.decode_8bpp_tiles(data)
                canvas = join_blocks(tiles.reshape(8, 8, 8, 8), (8, 8))
                images.append(GBAGraphics.create_image(canvas, palette))
            yield images

    def duelist_sprite_bitmap(self, duelist_index, variation_index):
        mem_bitmaps = self.rom[YugiohROM.CHARACTERS_BITMAPS]
        p_duelist_bitmaps = mem_bitmaps.read_pointers(29)
        if duelist_index < 0 or duelist_index >= len(p_duelist_bitmaps):
            raise IndexError(
                f"duelist_index must be between 0 and {len(p_duelist_bitmaps) - 1}"
            )

        p_variations = self.rom.read_pointers(
            5, offset=p_duelist_bitmaps[duelist_index]
        )
        if variation_index < 0 or variation_index >= len(p_variations):
            raise IndexError(
                f"variation_index must be between 0 and {len(p_variations) - 1}"
            )

        return self.rom[p_variations[variation_index], 4096]

    def duelist_sprite_palette(self, duelist_index):
        mem_palettes = self.rom[YugiohROM.CHARACTERS_PALETTES]
        p_duelist_palette = mem_palettes.read_pointers(29)
        if duelist_index < 0 or duelist_index >= len(p_duelist_palette):
            raise IndexError(
                f"duelist_index must be between 0 and {len(p_duelist_palette) - 1}"
            )

        return self.rom[p_duelist_palette[duelist_index], 128]

    def location_thumbs(self):
        base = YugiohROM.ACADEMY_LOCATIONS_THUMBS.start
        p_bitmap_tables = self.rom[base, 12].read_pointers(3)
        p_palette_tables = self.rom[base + 12, 12].read_pointers(3)
        for p_bm_table, p_pal_table in zip(p_bitmap_tables, p_palette_tables):
            p_bitmaps = self.rom.read_pointers(26, offset=p_bm_table)
            p_palettes = self.rom.read_pointers(26, offset=p_pal_table)
            images = []
            for p_bmp, p_pal in zip(p_bitmaps, p_palettes):
                data = self.rom.read_bytes(6144, offset=p_bmp + 4)
                palette = self.rom.read_array(128, offset=p_pal)
                tiles = GBAGraphics.decode_8bpp_tiles(data)
                canvas = join_blocks(tiles.reshape(8, 12, 8, 8), (8, 12))
                images.append(GBAGraphics.create_image(canvas, palette))
            yield images

    def location_thumb_bitmap(self, period_index, location_index):
        base = YugiohROM.ACADEMY_LOCATIONS_THUMBS.start
        p_bitmap_tables = self.rom[base, 12].read_pointers(3)
        p_bm_table = p_bitmap_tables[period_index]
        p_bitmaps = self.rom.read_pointers(26, offset=p_bm_table)
        p_bmp = p_bitmaps[location_index]
        return self.rom[p_bmp + 4, 6144]

    def location_thumb_palette(self, period_index, location_index):
        base = YugiohROM.ACADEMY_LOCATIONS_THUMBS.start
        p_palette_tables = self.rom[base + 12, 12].read_pointers(3)
        p_pal_table = p_palette_tables[period_index]
        p_palettes = self.rom.read_pointers(26, offset=p_pal_table)
        p_pal = p_palettes[location_index]
        return self.rom[p_pal, 128]

    def token_sprites(self):
        mem = self.rom[YugiohROM.TOKEN_SPRITES]
        p_tokens = mem.read_pointers(14)
        for p_token in p_tokens:
            palette = self.rom.read_array(128, offset=p_token)
            data = self.rom.read_bytes(6400, offset=p_token + 0x80)
            tiles = GBAGraphics.decode_8bpp_tiles(data)
            canvas = join_blocks(tiles.reshape(10, 10, 8, 8), (10, 10))
            yield GBAGraphics.create_image(canvas, palette)

    def token_sprite(self, index):
        num_tokens = 14
        if index < 0 or index >= num_tokens:
            raise IndexError(
                f"token index must be between 0 and {num_tokens - 1}, got {index}"
            )
        mem = self.rom[YugiohROM.TOKEN_SPRITES]
        p_tokens = mem.read_pointers(num_tokens)
        p_token = p_tokens[index]
        palette = self.rom.read_array(128, offset=p_token)
        data = self.rom.read_bytes(6400, offset=p_token + 0x80)
        tiles = GBAGraphics.decode_8bpp_tiles(data)
        canvas = join_blocks(tiles.reshape(10, 10, 8, 8), (10, 10))
        return GBAGraphics.create_image(canvas, palette)

    def card_pile_backgrounds(self):
        mem = self.rom[YugiohROM.DUEL_FIELD_BG]
        p_entries = mem.read_pointers(8)
        for p_entry in p_entries:
            yield self._decode_card_pile(p_entry)

    def card_pile_background(self, index):
        if index < 0 or index >= 8:
            raise IndexError(f"card_pile index must be between 0 and 7, got {index}")
        mem = self.rom[YugiohROM.DUEL_FIELD_BG]
        p_entries = mem.read_pointers(8)
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
            src = pair_data[i * 4] | (pair_data[i * 4 + 1] << 8)
            dst = pair_data[i * 4 + 2] | (pair_data[i * 4 + 3] << 8)
            src_tile = src & 0x3F
            if src_tile > 31:
                src_tile -= 32
            position = src_tile | ((src & 0xFF00) >> 3)
            screen_map[position] = dst
        if not screen_map:
            return None
        max_pos = max(screen_map.keys())
        map_w = 32
        map_h = (max_pos // map_w) + 1
        canvas = np.zeros((map_h * 8, map_w * 8), dtype=np.uint8)
        for pos, dst in screen_map.items():
            ty = pos // map_w
            tx = pos % map_w
            dst_tile = dst & 0x3FF
            hf = (dst >> 10) & 1
            vf = (dst >> 11) & 1
            bank = (dst >> 12) & 0xF
            if dst_tile < tile_count:
                tile = tiles[dst_tile].copy()
                if hf:
                    tile = np.fliplr(tile)
                if vf:
                    tile = np.flipud(tile)
                canvas[ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8] = tile + bank * 16
        rows = np.any(canvas != 0, axis=1)
        cols = np.any(canvas != 0, axis=0)
        if not rows.any():
            return None
        y0, y1 = np.where(rows)[0][[0, -1]]
        x0, x1 = np.where(cols)[0][[0, -1]]
        y0 = (y0 // 8) * 8
        x0 = (x0 // 8) * 8
        y1 = (y1 // 8 + 1) * 8
        x1 = (x1 // 8 + 1) * 8
        canvas = canvas[y0:y1, x0:x1]
        palette = bytearray()
        for j in range(256):
            if j < pal_n:
                v = pal_payload[j * 2] | (pal_payload[j * 2 + 1] << 8)
            else:
                v = 0x7C1F
            palette.extend([v & 0xFF, (v >> 8) & 0xFF])
        image = Image.fromarray(canvas)
        image.putpalette(palette, rawmode="RGB;15")
        return image

    def card_pile_background_layers(self, index):
        if index < 0 or index >= 8:
            raise IndexError(f"card_pile index must be between 0 and 7, got {index}")
        mem = self.rom[YugiohROM.DUEL_FIELD_BG]
        p_entries = mem.read_pointers(8)
        return self._decode_card_pile_layers(p_entries[index])

    def _decode_card_pile_layers(self, p_entry):
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
        layers = {}
        for i in range(num_pairs):
            src = pair_data[i * 4] | (pair_data[i * 4 + 1] << 8)
            dst = pair_data[i * 4 + 2] | (pair_data[i * 4 + 3] << 8)
            src_tile = src & 0x3F
            if src_tile > 31:
                src_tile -= 32
            position = src_tile | ((src & 0xFF00) >> 3)
            dst_tile = dst & 0x3FF
            hf = (dst >> 10) & 1
            vf = (dst >> 11) & 1
            bank = (dst >> 12) & 0xF
            if dst_tile >= tile_count:
                continue
            tile = tiles[dst_tile].copy()
            if hf:
                tile = np.fliplr(tile)
            if vf:
                tile = np.flipud(tile)
            ty = position // 32
            tx = position % 32
            if bank not in layers:
                layers[bank] = np.zeros((20 * 8, 32 * 8), dtype=np.uint8)
            layers[bank][ty * 8 : (ty + 1) * 8, tx * 8 : (tx + 1) * 8] = tile
        for bank in layers:
            layers[bank] = layers[bank][:, :240]
        return layers, pal_n, pal_payload

    @staticmethod
    def encode_card_pile_background(layers, pal_n, pal_payload):
        all_tiles = []
        tile_index = {}
        pairs = []
        h, w = 160, 240
        for row in range(h // 8):
            for col in range(w // 8):
                placer = None
                for bank in sorted(layers.keys()):
                    arr = np.asarray(layers[bank])
                    tile = arr[row * 8 : (row + 1) * 8, col * 8 : (col + 1) * 8]
                    if tile.max() != 0 or tile.min() != 0:
                        placer = (bank, tile.copy())
                        break
                if placer is None:
                    continue
                bank, tile = placer
                candidates = [
                    (tile.tobytes(), 0, 0),
                    (np.fliplr(tile).tobytes(), 1, 0),
                    (np.flipud(tile).tobytes(), 0, 1),
                    (np.flipud(np.fliplr(tile)).tobytes(), 1, 1),
                ]
                match = None
                for key, hf, vf in candidates:
                    if key in tile_index:
                        match = (tile_index[key], hf, vf)
                        break
                if match is None:
                    key = tile.tobytes()
                    tile_index[key] = len(all_tiles)
                    all_tiles.append(tile)
                    match = (tile_index[key], 0, 0)
                idx, hf, vf = match
                src = (row << 8) | col
                dst = idx | (hf << 10) | (vf << 11) | (bank << 12)
                pairs.append((src, dst))
        tile_count = len(all_tiles)
        tile_data = bytearray()
        for tile in all_tiles:
            for py in range(8):
                for col in range(0, 8, 2):
                    b = (int(tile[py, col]) << 4) | int(tile[py, col + 1])
                    tile_data.append(b)
        pairs.sort(key=lambda x: x[0])
        num_pairs = len(pairs)
        pair_bytes = bytearray()
        for src, dst in pairs:
            pair_bytes.extend([src & 0xFF, (src >> 8) & 0xFF])
            pair_bytes.extend([dst & 0xFF, (dst >> 8) & 0xFF])
        output = bytearray()
        for _ in range(4):
            output.extend([pal_n & 0xFF, (pal_n >> 8) & 0xFF])
        output.extend(pal_payload)
        output.extend([tile_count & 0xFF, (tile_count >> 8) & 0xFF])
        output.extend([0] * 6)
        output.extend(tile_data)
        output.extend([num_pairs & 0xFF, (num_pairs >> 8) & 0xFF])
        output.extend([0] * 6)
        output.extend(pair_bytes)
        return bytes(output)

    def patch_card_pile_background(self, index, layers):
        if index < 0 or index >= 8:
            raise IndexError(f"card_pile index must be between 0 and 7, got {index}")
        mem = self.rom[YugiohROM.DUEL_FIELD_BG]
        p_entries = mem.read_pointers(8)
        p_entry = p_entries[index]
        if index < 7:
            max_size = p_entries[index + 1] - p_entry
        else:
            max_size = YugiohROM.DUEL_FIELD_BG.stop - p_entry
        _, pal_n, pal_payload = self._decode_card_pile_layers(p_entry)
        encoded = self.encode_card_pile_background(layers, pal_n, pal_payload)
        if len(encoded) > max_size:
            raise ValueError(
                f"Encoded data ({len(encoded)} bytes) exceeds slot ({max_size} bytes)"
            )
        padded = encoded + b"\x00" * (max_size - len(encoded))
        self.rom[mem_region(p_entry, max_size)] = padded

    def card_filter_icons(self):
        """
        Returns the 6 Card Filter icons (16x16 each) as a combined image strip.
        Layout at 0x0945C338:
          - Top halves: tiles 0-11 (6 icons × 2 tiles wide)
          - Bottom halves: tiles 12-23 (6 icons × 2 tiles wide)
        Palette at 0x0945C318 (static, 16 colors).
        """
        base_addr = 0x0945C338
        pal_data = self.rom.read_bytes(32, offset=0x0945C318)

        data = self.rom.read_bytes(24 * 32, offset=base_addr)
        tiles = GBAGraphics.decode_4bpp_tiles(data)

        canvas = np.zeros((16, 6 * 16), dtype=np.uint8)

        for i in range(6):
            t_tl = tiles[i * 2]
            t_tr = tiles[i * 2 + 1]
            t_bl = tiles[12 + i * 2]
            t_br = tiles[12 + i * 2 + 1]

            x = i * 16
            canvas[0:8, x : x + 8] = t_tl
            canvas[0:8, x + 8 : x + 16] = t_tr
            canvas[8:16, x : x + 8] = t_bl
            canvas[8:16, x + 8 : x + 16] = t_br

        return GBAGraphics.create_image(canvas, pal_data)

    def selection_outlines(self, rank=0):
        """Returns the 10 selection outline tiles (80x8 pixels) using rank-based palettes."""
        addr = 0x0945D138
        pal_addr = 0x0945D0D8 + (rank * 32)

        data = self.rom.read_bytes(10 * 32, offset=addr)
        pal_data = self.rom.read_bytes(32, offset=pal_addr)

        tiles = GBAGraphics.decode_4bpp_tiles(data)
        canvas = np.hstack(tiles)  # Simple horizontal strip

        return GBAGraphics.create_image(canvas, pal_data)
