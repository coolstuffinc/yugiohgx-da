from .memory    import *
from .utils     import *
from .gba       import GBAHeader
from .passwords import YugiohPasswords
from PIL import Image

class YugiohROM:
    # Memory Mapping
    CARD_TOTAL_NUMBER      = mem_region(0x087a8620,4) # A integer with value 1200
    # Graphics
    CARD_HIGH_RES_PALETTES = mem_region(0x087aa24c,1201* 128) # 128  B each card palette
    CARD_HIGH_RES_BITMAPS  = mem_region(0x087cfacc,1201*6400) #  64 KB each card bitmap
    ACADEMY_LOCATIONS_THUMBS = slice(0x09772e14,0x097d549f)
    # English
    # - string section
    CARD_NAMES_EN          = slice(0x08f25690,0x08f2a68b) # 0x00, 0x00, Blue...
    CARD_TEXTS_EN          = slice(0x08f2b950,0x08f58293) # 0x00, 0x00, This lege...
    CARD_SHOP_PACK_INFO_EN = slice(0x094edd78,0x094eef57) # Basic 1-A, I recom ...
    TUTORIAL_DIALOGUES_EN  = slice(0x09472826,0x0947eba0) # On the duel screen, ...
    GAME_UI_STRINGS_EN     = slice(0x093f6df0,0x094280a0)
    # - offsets
    CARD_NAMES_OFFSETS_EN  = mem_region(0x08f2a68c,1201*4) # 1201 ints (4 Bytes each)
    CARD_TEXTS_OFFSETS_EN  = mem_region(0x08f58294,1201*4) #
    GAME_UI_OFFSETS_EN     = mem_region(0x094280b0,4524*4) #
    # - pointers
    TUTORIAL_INSTRUCT_EN   = mem_region(0x097fd78c,  68*4) # 68 Pointers to Strings 
    TUTORIAL_SECTIONS_EN   = mem_region(0x097fd78c,  11*4) # 11 Pointers to Strings 
    CHARS_FULL_NAMES_EN    = mem_region(0x097f0bc8,  36*4) # 36 Pointers to Strings
    CHARS_SHORT_NAMES_EN   = mem_region(0x097f0c58,  36*4) # 36 Pointers to Strings
    PLACES_NAMES_EN        = mem_region(0x097f0ce8,  26*4) # 26 Pointers to Strings
    DUELIST_TITLES_EN      = mem_region(0x097f0d50,  14*4) # 14 ..
    ACADEMY_DORMS_EN       = mem_region(0x097f0d88,   3*4) #  3 ..
    CARD_MONSTER_TYPES_EN  = mem_region(0x097d7b38,  24*4) # 24 ..
    CARD_MONSTER_ATTRS_EN  = mem_region(0x097d7b9c,   7*4) #  7 ..
    CARD_TYPES_EN          = mem_region(0x097d7bb8,   7*4) #  7 ..
    # Japanese
    # - string section
    CARD_NAMES_JP          = slice(0x08f5b180,0x08f61183)  # 0x00, 0x00, ブルーアイズ...
    CARD_TEXTS_JP          = slice(0)
    # - offsets
    CARD_NAMES_OFFSETS_JP  = mem_region(0x08f59ebc,1201*4) # 1201 ints (4 Bytes each)
    CARD_TEXTS_OFFSETS_JP  = slice(0)
    # - structs
    EVENT_NAMES_JP         = mem_region(0x0942c760,71*516) # 71 Structured Data
    # - pointers
    OPPONENT_NAMES_JP      = mem_region(0x097f468c,36*4)   # 36 Pointers to Strings
    EXAM_TYPE_JP           = mem_region(0x097f471c, 7*4)   #  7 Pointers to Strings
    # DATA
    #
    CARD_TOKEN_INFO        = slice(0x090a0540,0x090a0610)
    # LUT
    # - Ordinal number to id
    CARD_NUMBER_TO_ID      = mem_region(0x087a8624,1201*2) # 1201 words (2 Bytes)
    # - Event to related Player ID
    EVENT_TO_PLAYER_ID     = mem_region(0x0942c760, 150*2)
    # - Card password keys
    CARD_PASSWORD_KEYS     = mem_region(0x087a8f88,1201*4) # 1201 ints (4 Bytes)
    # MISC strings
    LICENSED_BY_1 = mem_region(0x0946c5f0,21)
    LICENSED_BY_2 = mem_region(0x097d5f24,21)

    def __init__(self, filename, memory_map=None):
        self.rom        = MemoryEmulator(filename)
        self.header     = GBAHeader(self._read_header())
        self.num_cards  = self._read_card_total_number() # This is used afterwards
        self.card_names  = self._read_card_names()
        self.card_texts  = self._read_card_texts()
        self.card_images = self._read_card_artworks()
        self.card_thumbs = self._read_card_thumbnails()
        self.passwords   = YugiohPasswords(self._read_card_password_keys())
        card_number_id   = self._read_card_number_to_id()

    @property
    def game_title(self):
        """ Returns the Game Title YUGIOHGXDA """ 
        return charset_decode(self.header.game_title)

    @property
    def rom_entry_point(self):
        return hex(self.header.rom_entry_point)

    @property
    def game_code(self):
        return charset_decode(self.header.game_code)

    def patch(self, patched: MemoryEmulator):
        """ Update a memory region with new contents """
        self.rom[patched.region] = patched._payload

    def save(self, filename):
        """ Write modified rom data to a file """
        self.rom.write(filename)

    def card_image(self, card_id):
        """ Returns memory region for a card artwork """
        start = YugiohROM.CARD_HIGH_RES_BITMAPS.start
        card_bitmap = self.rom[start+6400*card_id:start+6400*(card_id+1)]
        return card_bitmap

    def card_text(self, card_id):
        """ Returns memory region for a card text """
        offsets = YugiohROM.CARD_TEXTS_OFFSETS_EN
        strings = YugiohROM.CARD_TEXTS_EN
        card_text = self._read_string_with_offset(card_id, strings, offsets)
        return card_text

    def card_name(self, card_id):
        """ Returns memory region for a card name """
        offsets = YugiohROM.CARD_NAMES_OFFSETS_EN
        strings = YugiohROM.CARD_NAMES_EN
        card_name = self._read_string_with_offset(card_id, strings, offsets)
        return card_name

    def _read_string_with_offset(self, string_id, string_region, offset_region, offset_size=4):
        """ Read one string from memory region given a offset table """
        mem_offsets = self.rom[offset_region]
        elements = len(mem_offsets) // offset_size
        # This assumes that each offset is 4 bytes long
        offsets = mem_offsets.read_array(elements,dtype='I')
        string_base  = string_region.start
        string_start = string_base + offsets[string_id]
        string_stop  = string_base + offsets[string_id+1] - 1
        memory = self.rom[string_start:string_stop]
        return memory

    def _read_all_strings(self, string_region, offset_region, offset_size=4):
        """ Returns a list with all strings given a offset table """
        mem_strings = self.rom[string_region]
        mem_offsets = self.rom[offset_region]
        elements = len(mem_offsets) // offset_size
        # This assumes that each offset is 4 bytes long
        offsets = mem_offsets.read_array(elements,dtype='I')
        sizes   = sucessive_sub(offsets)

        strings = []
        for offset, size in zip(offsets,sizes):
            data = mem_strings.read_struct(f'<{size}s', offset=offset)
            string = charset_decode(data)
            strings.append(string)
        return strings

    def _read_header(self):
        """ Returns the struct payload with header info """
        data = self.rom.read_struct(GBAHeader.STRUCT_FMT)
        return data

    def _read_card_number_to_id(self):
        """ Returns a LUT to convert card number to id """
        LUT = self.rom[YugiohROM.CARD_NUMBER_TO_ID]
        return LUT.read_array(1201,dtype='H')

    def _read_card_password_keys(self):
        """ Returns password decryption keys """
        keys = self.rom[YugiohROM.CARD_PASSWORD_KEYS]
        return keys.read_array(1201,dtype='I')

    def _read_card_total_number(self):
        """ Returns 1200 """
        num_cards = self.rom[YugiohROM.CARD_TOTAL_NUMBER]
        return num_cards.read_integer(1)

    def _read_card_names(self):
        """ Returns a list with the english card names """
        strings = YugiohROM.CARD_NAMES_EN
        offsets = YugiohROM.CARD_NAMES_OFFSETS_EN
        return self._read_all_strings(strings,offsets)

    def _read_card_texts(self):
        """ Returns a list with all english card texts """
        strings = YugiohROM.CARD_TEXTS_EN
        offsets = YugiohROM.CARD_TEXTS_OFFSETS_EN
        return self._read_all_strings(strings,offsets)

    def _read_hi_card_palettes(self):
        """ Reads palettes for 80x80px card artworks: 8bpp """
        palettes = self.rom[YugiohROM.CARD_HIGH_RES_PALETTES]
        shape = (1201,128)
        data = palettes.read_array(shape,dtype='B') # words
        return data

    def _read_hi_card_bitmaps(self):
        """ Reads bitmaps for 80x80px card artworks """
        bitmaps = self.rom[YugiohROM.CARD_HIGH_RES_BITMAPS]
        shape = (1201,80*80)
        data = bitmaps.read_array(shape,dtype='B') # words
        return data

    def _read_lo_card_palettes(self):
        """ Reads palettes for low res card artworks """
        raise NotImplementedError
        return
        palettes = self.rom[0x08f61184:0x08f61184+1201*64] 
        shape = (1201,64)
        data = palettes.read_array(shape,dtype='B') # words
        return data

    def _read_lo_card_bitmaps(self):
        """ Reads bitmaps for low res card artworks """
        raise NotImplementedError
        return 

    def _read_card_artworks(self):
        """ Returns a generator with artwork for each card """
        hires_bmp = self._read_hi_card_bitmaps()
        hires_pal = self._read_hi_card_palettes()
        bmp = hires_bmp.reshape(1201,10,10,8,8)
        pal = hires_pal
        for idx in range(self.num_cards):
            bitmap  = bmp[idx]
            palette = pal[idx]
            blocks = [[bitmap[i,j] for j in range(10)]
                                   for i in range(10)]
            array = np.block(blocks)
            image = Image.fromarray(array)
            image.putpalette(palette, rawmode="RGB;15")
            yield image

    def _read_card_thumbnails(self):
        """ Returns a generator with thumbnails for each card """
        raise NotImplementedError
        return
        # FIXME under construction: showing the palettes
        #low_bmp = self._read_lo_card_bitmaps()
        #low_pal = self._read_lo_card_palettes()
        #bmp = hires_bmp.reshape(1201,10,10,8,8)
        pal = low_pal.reshape(1201,8,8)
        for idx in range(self.num_cards):
            palette = pal[idx]
            image = Image.new("RGB",palette.shape)
            data = tuple(map(gba2rgb,palette.flatten()))
            image.putdata(data)
            yield image
