from dataclasses import dataclass

from .rom import YugiohROM


@dataclass(frozen=True)
class MemoryPath:
    path: str
    region: slice
    description: str

    @property
    def size(self) -> int:
        return int(self.region.stop - self.region.start)


@dataclass(frozen=True)
class StringTable:
    name: str
    strings_path: str
    offsets_path: str
    description: str
    encoding: str = "utf-8"


CANONICAL_MEMORY_PATHS = {
    "cards.high_res.palettes": MemoryPath(
        "cards.high_res.palettes",
        YugiohROM.CARD_HIGH_RES_PALETTES,
        "High-resolution card palettes",
    ),
    "cards.high_res.bitmaps": MemoryPath(
        "cards.high_res.bitmaps",
        YugiohROM.CARD_HIGH_RES_BITMAPS,
        "High-resolution card bitmaps",
    ),
    "sprites.characters.bitmaps": MemoryPath(
        "sprites.characters.bitmaps",
        YugiohROM.CHARACTERS_BITMAPS,
        "Duelist sprite bitmap pointer tables",
    ),
    "sprites.characters.palettes": MemoryPath(
        "sprites.characters.palettes",
        YugiohROM.CHARACTERS_PALETTES,
        "Duelist sprite palette pointer tables",
    ),
    "sprites.locations.thumbs": MemoryPath(
        "sprites.locations.thumbs",
        YugiohROM.ACADEMY_LOCATIONS_THUMBS,
        "Academy location thumbnail pointer tables",
    ),
    "sprites.card_piles": MemoryPath(
        "sprites.card_piles",
        YugiohROM.DUEL_FIELD_BG,
        "Card pile background BIG_3 entries (8)",
    ),
    "strings.cards.names.en": MemoryPath(
        "strings.cards.names.en",
        YugiohROM.CARD_NAMES_EN,
        "English card names string table payload",
    ),
    "strings.cards.names.en.offsets": MemoryPath(
        "strings.cards.names.en.offsets",
        YugiohROM.CARD_NAMES_OFFSETS_EN,
        "English card names offset table",
    ),
    "strings.cards.names.jp": MemoryPath(
        "strings.cards.names.jp",
        YugiohROM.CARD_NAMES_JP,
        "Japanese card names string table payload",
    ),
    "strings.cards.names.jp.offsets": MemoryPath(
        "strings.cards.names.jp.offsets",
        YugiohROM.CARD_NAMES_OFFSETS_JP,
        "Japanese card names offset table",
    ),
    "strings.cards.texts.en": MemoryPath(
        "strings.cards.texts.en",
        YugiohROM.CARD_TEXTS_EN,
        "English card text string table payload",
    ),
    "strings.cards.texts.en.offsets": MemoryPath(
        "strings.cards.texts.en.offsets",
        YugiohROM.CARD_TEXTS_OFFSETS_EN,
        "English card text offset table",
    ),
    "strings.ui.en": MemoryPath(
        "strings.ui.en",
        YugiohROM.GAME_UI_STRINGS_EN,
        "English game UI strings payload",
    ),
    "strings.ui.en.offsets": MemoryPath(
        "strings.ui.en.offsets",
        YugiohROM.GAME_UI_OFFSETS_EN,
        "English game UI offset table",
    ),
}


CANONICAL_STRING_TABLES = {
    "card_names_en": StringTable(
        "card_names_en",
        "strings.cards.names.en",
        "strings.cards.names.en.offsets",
        "Card names in English",
    ),
    "card_names_jp": StringTable(
        "card_names_jp",
        "strings.cards.names.jp",
        "strings.cards.names.jp.offsets",
        "Card names in Japanese",
        encoding="japanese_rom",
    ),
    "card_texts_en": StringTable(
        "card_texts_en",
        "strings.cards.texts.en",
        "strings.cards.texts.en.offsets",
        "Card texts in English",
    ),
    "ui_en": StringTable(
        "ui_en",
        "strings.ui.en",
        "strings.ui.en.offsets",
        "Game UI strings in English",
    ),
}


def resolve_memory_path(path: str) -> MemoryPath:
    try:
        return CANONICAL_MEMORY_PATHS[path]
    except KeyError as exc:
        raise KeyError(f"Unknown memory path: {path}") from exc


def resolve_string_table(name: str) -> StringTable:
    try:
        return CANONICAL_STRING_TABLES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown string table: {name}") from exc


def list_memory_paths():
    return tuple(CANONICAL_MEMORY_PATHS[key] for key in sorted(CANONICAL_MEMORY_PATHS))
