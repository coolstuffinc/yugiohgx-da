from dataclasses import dataclass, field
from typing import Optional, Tuple, Callable, Any, Dict, List, Union
import numpy as np
from PIL import Image

from .graphics import GBAGraphics
from .utils import join_blocks, split_blocks, sucessive_sub, charset_decode
from .memory import MemoryEmulator, mem_region as slice_region


@dataclass
class ROMRegion:
    name: str
    start: int
    end: int
    description: str
    category: str = "unknown"

    @property
    def slice(self) -> slice:
        return slice(self.start, self.end)

    @property
    def size(self) -> int:
        return self.end - self.start

    @property
    def path(self) -> str:  # Compatibility with old tests
        return self.name


@dataclass
class StringTableMetadata:
    name: str
    strings_region: str
    offsets_region: str
    description: str
    encoding: str = "utf-8"


@dataclass
class SpriteMetadata:
    name: str
    width: int
    height: int
    bpp: int
    palette_colors: int
    palette_offset: int = 0
    count: int = 1
    variations: int = 1
    is_pointer_table: bool = False
    pointers_are_packed: bool = False
    bitmap_region: str = ""
    palette_region: str = ""
    entry_stride: int = 0
    palette_stride: int = 0
    root_table_size: int = 0
    bitmap_header_skip: int = 0


@dataclass
class SpriteCollection:
    resource: SpriteMetadata
    getter: Callable[[Any, int, int], Tuple[bytes, bytes]]
    setter: Callable[[Any, int, bytes, bytes, int], None]

    def get(self, rom: Any, index: int, variation: int = 0) -> Image.Image:
        bmp, pal = self.getter(rom, index, variation)
        if isinstance(bmp, Image.Image):
            return bmp
        return self.decode(bmp, pal)

    def patch(self, rom: Any, index: int, image: Image.Image, variation: int = 0):
        bmp, pal = self.encode(image)
        self.setter(rom, index, bmp, pal, variation)

    def decode(self, bitmap_bytes: bytes, palette_bytes: bytes) -> Image.Image:
        if self.resource.bpp == 4:
            tiles = GBAGraphics.decode_4bpp_tiles(bitmap_bytes)
        else:
            tiles = GBAGraphics.decode_8bpp_tiles(bitmap_bytes)
        blocks = (self.resource.height // 8, self.resource.width // 8)
        canvas = join_blocks(tiles.reshape(*blocks, 8, 8), blocks)
        full_pal = bytearray(512)
        start, size = self.resource.palette_offset * 2, self.resource.palette_colors * 2
        full_pal[start : start + size] = palette_bytes[:size]
        if self.resource.palette_offset != 0:
            mask = canvas != 0
            canvas[mask] = (
                canvas[mask].astype(np.uint16) + self.resource.palette_offset
            ) & 0xFF
        return GBAGraphics.create_image(canvas, full_pal)

    def encode(self, image: Image.Image) -> Tuple[bytes, bytes]:
        if image.size != (self.resource.width, self.resource.height):
            image = image.resize(
                (self.resource.width, self.resource.height), Image.Resampling.NEAREST
            )
        if image.mode != "P":
            image = image.convert("P")
        pixels = np.asarray(image, dtype=np.uint8)
        if self.resource.palette_offset != 0:
            mask = pixels >= self.resource.palette_offset
            pixels = pixels.copy()
            pixels[mask] -= self.resource.palette_offset
            pixels[~mask] = 0
        blocks = (self.resource.height // 8, self.resource.width // 8)
        tiles = split_blocks(pixels, blocks)
        bitmap_bytes = (
            GBAGraphics.encode_4bpp_tiles(tiles)
            if self.resource.bpp == 4
            else GBAGraphics.encode_8bpp_tiles(tiles)
        )
        from .utils import rgb2gba

        raw_pal = image.getpalette() or [0] * 768
        gba_pal = [
            rgb2gba(*raw_pal[i * 3 : i * 3 + 3])
            for i in range(
                self.resource.palette_offset,
                self.resource.palette_offset + self.resource.palette_colors,
            )
        ]
        return bitmap_bytes, np.asarray(gba_pal, dtype="<u2").tobytes()


class AssetRegistry:
    def __init__(self):
        self.regions: Dict[str, ROMRegion] = {}
        self.string_tables: Dict[str, StringTableMetadata] = {}
        self.sprites: Dict[str, SpriteMetadata] = {}

    def reg(self, n, s, e, d, c="data"):
        self.regions[n] = ROMRegion(n, s, e, d, c)

    def reg_str(self, name, s_reg, o_reg, desc, enc="utf-8"):
        self.string_tables[name] = StringTableMetadata(name, s_reg, o_reg, desc, enc)

    def reg_sprite(
        self,
        name,
        w,
        h,
        bpp,
        pal_c,
        pal_off=0,
        count=1,
        vars=1,
        is_ptr=False,
        packed=False,
        b_reg="",
        p_reg="",
        e_stride=0,
        p_stride=0,
        root_table_size=0,
        bitmap_header_skip=0,
    ):
        self.sprites[name] = SpriteMetadata(
            name,
            w,
            h,
            bpp,
            pal_c,
            pal_off,
            count,
            vars,
            is_ptr,
            packed,
            b_reg,
            p_reg,
            e_stride,
            p_stride,
            root_table_size,
            bitmap_header_skip,
        )

    def get_region(self, name: str) -> ROMRegion:
        return self.regions[name]

    def find_region_at(self, address: int) -> Optional[ROMRegion]:
        for r in self.regions.values():
            if r.start <= address < r.end:
                return r
        return None


ASSETS = AssetRegistry()


def _init_registry():
    # Registry Initialization with exact names for compatibility
    ASSETS.reg("ROM_HEADER", 0x08000000, 0x080000C0, "GBA ROM header + BIOS", "code")
    ASSETS.reg(
        "INTERRUPT_BOOT",
        0x080000C0,
        0x08000230,
        "Interrupt vectors / boot code",
        "code",
    )
    ASSETS.reg("GAME_CODE_1", 0x08000230, 0x081EE230, "Main game logic", "code")
    ASSETS.reg("MATRIX1", 0x081EE230, 0x085E66C0, "Matrix section 1", "data")
    ASSETS.reg("GAME_CODE_2", 0x085E66C0, 0x08700000, "Game logic continued", "code")
    ASSETS.reg("CARD_TOTAL_NUMBER", 0x087A8620, 0x087A8624, "Card count")
    ASSETS.reg(
        "CARD_NUMBER_TO_ID", 0x087A8624, 0x087A8F86, "Card number -> ordinal LUT"
    )
    ASSETS.reg("CARD_PASSWORD_KEYS", 0x087A8F88, 0x087AA24C, "Password keys")
    ASSETS.reg("CARD_HIRES_PALETTES", 0x087AA24C, 0x087CFACC, "Card palettes")
    ASSETS.reg("CARD_HIRES_BITMAPS", 0x087CFACC, 0x08F243CC, "Card bitmaps")
    ASSETS.reg("CARD_STATS", 0x08F243CC, 0x08F25690, "Card stats")
    ASSETS.reg("CARD_NAMES_EN", 0x08F25690, 0x08F2A68B, "English card names", "strings")
    ASSETS.reg(
        "CARD_NAMES_OFFSETS_EN", 0x08F2A68C, 0x08F2B950, "English card names offsets"
    )
    ASSETS.reg("CARD_TEXTS_EN", 0x08F2B950, 0x08F58293, "English card texts", "strings")
    ASSETS.reg(
        "CARD_TEXTS_OFFSETS_EN", 0x08F58294, 0x08F59558, "English card text offsets"
    )
    ASSETS.reg(
        "CARD_NAMES_JP", 0x08F5B180, 0x08F61183, "Japanese card names", "strings"
    )
    ASSETS.reg(
        "CARD_NAMES_OFFSETS_JP", 0x08F59EBC, 0x08F5B180, "Japanese card name offsets"
    )
    ASSETS.reg("CHAR_BITMAPS", 0x091F24DC, 0x09250780, "Duelist bitmaps", "graphics")
    ASSETS.reg("CHAR_PALETTES", 0x09250780, 0x092515F4, "Duelist palettes", "graphics")
    ASSETS.reg(
        "CARD_PILE_BG", 0x092515F4, 0x093F6DF0, "Card pile backgrounds", "graphics"
    )
    ASSETS.reg("GAME_UI_STR_EN", 0x093F6DF0, 0x094280A0, "UI strings EN", "strings")
    ASSETS.reg("GAME_UI_OFFSETS_EN", 0x094280B0, 0x0942C75F, "UI offsets EN")
    ASSETS.reg(
        "CARD_PACK_BITMAPS", 0x0947EBB0, 0x094C21B0, "Card pack bitmaps", "graphics"
    )
    ASSETS.reg(
        "CARD_PACK_PALETTES", 0x094C2274, 0x094C34D4, "Card pack palettes", "graphics"
    )
    ASSETS.reg("CARD_PACK_TILEMAPS", 0x094C34D4, 0x094ECB18, "Card pack tilemaps")
    ASSETS.reg("CARD_SHOP_INFO", 0x094EDD78, 0x094EEF57, "Card shop info", "strings")
    ASSETS.reg(
        "LOC_THUMBNAILS", 0x09772E14, 0x097D549F, "Location thumbnails", "graphics"
    )
    ASSETS.reg(
        "ROOM_INTERACTION_TABLE", 0x097EDA00, 0x097EDE00, "Room interaction table"
    )
    ASSETS.reg("CARD_SPECIFIC_EFFECTS", 0x097DA800, 0x097E12B4, "Card effects")
    ASSETS.reg("ROM_END_UNKNOWN", 0x097FD89C, 0x0A000000, "ROM padding")

    # String Tables
    ASSETS.reg_str(
        "card_names_en", "CARD_NAMES_EN", "CARD_NAMES_OFFSETS_EN", "Card names EN"
    )
    ASSETS.reg_str(
        "card_names_jp",
        "CARD_NAMES_JP",
        "CARD_NAMES_OFFSETS_JP",
        "Card names JP",
        "japanese_rom",
    )
    ASSETS.reg_str(
        "card_texts_en", "CARD_TEXTS_EN", "CARD_TEXTS_OFFSETS_EN", "Card texts EN"
    )
    ASSETS.reg_str("ui_en", "GAME_UI_STR_EN", "GAME_UI_OFFSETS_EN", "Game UI EN")

    # Sprite Collections (Keys match expected CLI/test strings)
    ASSETS.reg_sprite(
        "card",
        80,
        80,
        8,
        64,
        count=1201,
        b_reg="CARD_HIRES_BITMAPS",
        p_reg="CARD_HIRES_PALETTES",
        e_stride=6400,
        p_stride=128,
    )
    ASSETS.reg_sprite(
        "duelist",
        64,
        64,
        8,
        64,
        count=29,
        vars=5,
        is_ptr=True,
        b_reg="CHAR_BITMAPS",
        p_reg="CHAR_PALETTES",
    )
    ASSETS.reg_sprite(
        "location-thumb",
        96,
        64,
        8,
        64,
        count=26,
        vars=3,
        is_ptr=True,
        packed=False,
        b_reg="LOC_THUMBNAILS",
        p_reg="LOC_THUMBNAILS",
        root_table_size=6,
        bitmap_header_skip=4,
    )
    ASSETS.reg_sprite(
        "card-pack",
        64,
        88,
        8,
        48,
        160,
        count=49,
        is_ptr=True,
        b_reg="CARD_PACK_BITMAPS",
        p_reg="CARD_PACK_PALETTES",
        p_stride=96,
    )
    ASSETS.reg_sprite(
        "card-pile",
        256,
        160,
        4,
        16,
        count=8,
        is_ptr=True,
        b_reg="CARD_PILE_BG",
        root_table_size=8,
    )


_init_registry()
ROM_LAYOUT = list(ASSETS.regions.values())
