from dataclasses import dataclass


@dataclass
class ROMRegion:
    name: str
    start: int
    end: int
    description: str
    category: str = ""  # code, graphics, strings, data, unknown


ROM_LAYOUT = [
    # Code section (0x08000000)
    ROMRegion("ROM_HEADER", 0x08000000, 0x080000C0, "GBA ROM header + BIOS", "code"),
    ROMRegion(
        "INTERRUPT_BOOT",
        0x080000C0,
        0x08000230,
        "Interrupt vectors / boot code",
        "code",
    ),
    ROMRegion(
        "GAME_CODE_1", 0x08000230, 0x081EE230, "Main game logic (~1976 KB)", "code"
    ),
    ROMRegion(
        "MATRIX1",
        0x081EE230,
        0x085E66C0,
        "Matrix section 1 (~4 MB, compressed?)",
        "data",
    ),
    ROMRegion(
        "GAME_CODE_2", 0x085E66C0, 0x08700000, "Game logic continued (~1126 KB)", "code"
    ),
    # Data section (0x08700000)
    ROMRegion("DATA_ZEROS", 0x08700000, 0x08700818, "Zero padding", "data"),
    ROMRegion(
        "DATA_BLOCKS", 0x08700818, 0x087A8620, "Unknown data blocks (~671 KB)", "data"
    ),
    ROMRegion(
        "CARD_TOTAL_NUMBER",
        0x087A8620,
        0x087A8624,
        "Card count = 1200 (uint32)",
        "data",
    ),
    ROMRegion(
        "CARD_NUMBER_TO_ID",
        0x087A8624,
        0x087A8F86,
        "Card number -> ordinal LUT (1201 x uint16)",
        "data",
    ),
    ROMRegion("GAP", 0x087A8F86, 0x087A8F88, "2-byte gap", "gap"),
    ROMRegion(
        "CARD_PASSWORD_KEYS",
        0x087A8F88,
        0x087AA24C,
        "Password decryption keys (1201 x uint32)",
        "data",
    ),
    ROMRegion(
        "CARD_HIRES_PALETTES",
        0x087AA24C,
        0x087CFACC,
        "High-res card palettes (1201 x 128B)",
        "graphics",
    ),
    ROMRegion(
        "CARD_HIRES_BITMAPS",
        0x087CFACC,
        0x08F243CC,
        "High-res card bitmaps (1201 x 6400B)",
        "graphics",
    ),
    ROMRegion(
        "CARD_STATS",
        0x08F243CC,
        0x08F25690,
        "Card stats: attr|level|type|ATK|DEF bitfield (1201 x uint32)",
        "data",
    ),
    # English strings
    ROMRegion("CARD_NAMES_EN", 0x08F25690, 0x08F2A68B, "English card names", "strings"),
    ROMRegion(
        "CARD_NAMES_OFF_EN",
        0x08F2A68C,
        0x08F2B94F,
        "English card name offsets (1201 x uint32)",
        "data",
    ),
    ROMRegion("CARD_TEXTS_EN", 0x08F2B950, 0x08F58293, "English card texts", "strings"),
    ROMRegion(
        "CARD_TEXTS_OFF_EN",
        0x08F58294,
        0x08F59EBD,
        "English card text offsets (1201 x uint32)",
        "data",
    ),
    # Japanese strings
    ROMRegion(
        "CARD_NAMES_OFF_JP",
        0x08F59EBE,
        0x08F5B17F,
        "Japanese card name offsets (1201 x uint32)",
        "data",
    ),
    ROMRegion(
        "CARD_NAMES_JP", 0x08F5B180, 0x08F61183, "Japanese card names", "strings"
    ),
    # Large unknown region
    ROMRegion(
        "UNKNOWN_BIG_1",
        0x08F61183,
        0x090A0540,
        "4bpp tiled bitmaps: card shop, code entry UI, suitcase sprite (~1276 KB, 22 images)",
        "graphics",
    ),
    ROMRegion("CARD_TOKEN_INFO", 0x090A0540, 0x090A0610, "Token card data", "data"),
    ROMRegion(
        "TOKEN_SPRITES",
        0x090A0610,
        0x091F24DC,
        "Token sprites (14 entries, pointer table + 0x1980B each)",
        "graphics",
    ),
    # Character sprites
    ROMRegion(
        "CHAR_BITMAPS",
        0x091F24DC,
        0x09250780,
        "Duelist sprite bitmaps (29 chars x 5 poses)",
        "graphics",
    ),
    ROMRegion(
        "CHAR_PALETTES", 0x09250780, 0x092515F4, "Duelist sprite palettes", "graphics"
    ),
    ROMRegion(
        "DUEL_FIELD_BG",
        0x092515F4,
        0x093F6DF0,
        "Duel field backgrounds (8 entries, 240x160 4bpp tiled)",
        "graphics",
    ),
    # UI strings
    ROMRegion(
        "GAME_UI_STR_EN", 0x093F6DF0, 0x094280A0, "English UI strings", "strings"
    ),
    ROMRegion(
        "GAME_UI_OFF_EN",
        0x094280B0,
        0x0942C75F,
        "English UI string offsets (4524 x uint32)",
        "data",
    ),
    # Event data
    ROMRegion(
        "EVENT_DATA_JP",
        0x0942C760,
        0x09430BDF,
        "Event names (JP) / player ID LUT (71 x 516B)",
        "data",
    ),
    # Exam database
    ROMRegion(
        "EXAM_PTR_TABLE",
        0x09430BE0,
        0x09430F0F,
        "Exam DB pointer table (1200 x uint32)",
        "data",
    ),
    ROMRegion(
        "EXAM_STRUCTURES",
        0x09430F10,
        0x0946C5EF,
        "Exam question structures (variable len)",
        "data",
    ),
    # More strings
    ROMRegion("LICENSED_BY_1", 0x0946C5F0, 0x0946C604, "License string", "strings"),
    ROMRegion(
        "UNKNOWN_AFTER_LIC", 0x0946C604, 0x09472826, "Unknown (~24 KB)", "unknown"
    ),
    ROMRegion(
        "TUTORIAL_DIALOGUES",
        0x09472826,
        0x0947EBA0,
        "Tutorial dialogue strings",
        "strings",
    ),
    ROMRegion(
        "CARD_PACK_BITMAPS",
        0x0947EBB0,
        0x094C21B0,
        "Card pack portrait bitmaps (49 entries x 5632B, 8bpp raw tiles)",
        "graphics",
    ),
    ROMRegion(
        "CARD_PACK_PALETTES",
        0x094C2274,
        0x094C34D4,
        "Card pack portrait palettes (49 entries x 96B)",
        "graphics",
    ),
    ROMRegion(
        "CARD_PACK_TILEMAPS",
        0x094C34D4,
        0x094ECB18,
        "Card pack cover tilemaps (49 entries x 3456B, for shared tileset)",
        "data",
    ),
    ROMRegion(
        "UNKNOWN_AFTER_PACKS",
        0x094ECB18,
        0x094EDD78,
        "Unknown (~4 KB, after card pack tiles)",
        "unknown",
    ),
    # Shop
    ROMRegion(
        "CARD_SHOP_INFO",
        0x094EDD78,
        0x094EEF57,
        "Card shop pack info strings",
        "strings",
    ),
    ROMRegion(
        "CARD_PILE_GFX",
        0x094EEF57,
        0x09772E14,
        "Card-pile-format 4bpp graphics: 3D card rotation animation (panel + cropped variants), bg frames, UI panels (~2575 KB)",
        "graphics",
    ),
    # Location thumbnails
    ROMRegion(
        "LOC_THUMBNAILS",
        0x09772E14,
        0x097D549F,
        "Academy location thumbnails",
        "graphics",
    ),
    ROMRegion("LICENSED_2_PAD", 0x097D549F, 0x097D5F24, "License / padding", "strings"),
    # Name/type pointers
    ROMRegion(
        "MONSTER_TYPE_PTRS",
        0x097D7B38,
        0x097D7B9B,
        "Monster type name pointers (24)",
        "data",
    ),
    ROMRegion(
        "MONSTER_ATTR_PTRS",
        0x097D7B9C,
        0x097D7BB7,
        "Monster attribute name pointers (7)",
        "data",
    ),
    ROMRegion(
        "CARD_TYPE_PTRS", 0x097D7BB8, 0x097D7BF7, "Card type name pointers (7)", "data"
    ),
    ROMRegion(
        "CARD_SPECIFIC_EFFECTS",
        0x097DA800,
        0x097E12B4,
        "Card-specific effect handler table (~887 entries x 28B)",
        "data",
    ),
    ROMRegion(
        "STR_UNKNOWN_1A",
        0x097D7BF7,
        0x097DA800,
        "Unknown (~10 KB, before card effect table)",
        "unknown",
    ),
    ROMRegion(
        "UNKNOWN_BEFORE_ROOM_TABLE",
        0x097E12B4,
        0x097EDA00,
        "Unknown (~50 KB, before room interaction table)",
        "unknown",
    ),
    ROMRegion(
        "ROOM_INTERACTION_TABLE",
        0x097EDA00,
        0x097EDE00,
        "Room interaction table: header + month names + menu screen fns + handler dispatch",
        "data",
    ),
    ROMRegion(
        "UNKNOWN_AFTER_ROOM_TABLE",
        0x097EDE00,
        0x097F0BC8,
        "Unknown (~11 KB, after room interaction table)",
        "unknown",
    ),
    # Character names
    ROMRegion(
        "CHAR_NAMES_FULL",
        0x097F0BC8,
        0x097F0C57,
        "Character full names EN (36 ptrs)",
        "strings",
    ),
    ROMRegion(
        "CHAR_NAMES_SHORT",
        0x097F0C58,
        0x097F0CE7,
        "Character short names EN (36 ptrs)",
        "strings",
    ),
    ROMRegion(
        "LOC_NAMES",
        0x097F0CE8,
        0x097F0D4F,
        "Academy location names EN (26 ptrs)",
        "strings",
    ),
    ROMRegion(
        "DUELIST_TITLES",
        0x097F0D50,
        0x097F0D87,
        "Duelist title names (14 ptrs)",
        "strings",
    ),
    ROMRegion(
        "ACADEMY_DORMS",
        0x097F0D88,
        0x097F0DFF,
        "Academy dorm names (3 ptrs)",
        "strings",
    ),
    # More pointer tables
    ROMRegion(
        "UNKNOWN_PTRS",
        0x097F0DFF,
        0x097F468C,
        "Unknown ~14 KB (maybe more ptrs)",
        "unknown",
    ),
    ROMRegion(
        "OPPONENT_NAMES_JP",
        0x097F468C,
        0x097F471B,
        "Opponent names JP (36 ptrs)",
        "strings",
    ),
    ROMRegion(
        "EXAM_TYPE_JP", 0x097F471C, 0x097F4737, "Exam type names JP (7 ptrs)", "strings"
    ),
    ROMRegion("UNKNOWN_END_PTRS", 0x097F4738, 0x097FD78C, "Unknown ~36 KB", "unknown"),
    # Tutorial
    ROMRegion(
        "TUTORIAL_PTRS",
        0x097FD78C,
        0x097FD89C,
        "Tutorial instruct/sections (68+11 ptrs)",
        "data",
    ),
    # Rest of ROM
    ROMRegion(
        "ROM_END_UNKNOWN",
        0x097FD89C,
        0x0A000000,
        "Unknown / padding (~8201 KB)",
        "unknown",
    ),
]


def get_region(address):
    for r in ROM_LAYOUT:
        if r.start <= address < r.end:
            return r
    return None


def coverage_summary():
    categories = {}
    for r in ROM_LAYOUT:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"count": 0, "bytes": 0}
        categories[cat]["count"] += 1
        categories[cat]["bytes"] += r.end - r.start

    total = sum(c["bytes"] for c in categories.values())
    print(f"{'Category':<15} {'Count':>6} {'Bytes':>12} {'%':>8}")
    print("-" * 45)
    for cat in sorted(categories.keys()):
        c = categories[cat]
        pct = c["bytes"] / total * 100
        print(f"{cat:<15} {c['count']:>6} {c['bytes']:>12} {pct:>7.1f}%")
    print("-" * 45)
    print(
        f"{'TOTAL':<15} {sum(c['count'] for c in categories.values()):>6} {total:>12} {'100.0%':>8}"
    )


def print_map():
    print(f"{'Address':<12} {'End':<12} {'Size':>8} {'Category':<10} {'Description'}")
    print("-" * 80)
    for r in ROM_LAYOUT:
        size = r.end - r.start
        name = r.name[:30]
        print(
            f"0x{r.start:08X} 0x{r.end:08X} {size:>7}B {r.category:<10} {r.description}"
        )
