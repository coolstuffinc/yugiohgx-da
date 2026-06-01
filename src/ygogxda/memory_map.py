from .registry import ASSETS, ROM_LAYOUT, ROMRegion, StringTableMetadata

# Backward compatibility re-exports
CANONICAL_MEMORY_PATHS = {r.name: r for r in ASSETS.regions.values()}
CANONICAL_STRING_TABLES = ASSETS.string_tables

# Define types for compatibility
MemoryPath = ROMRegion
StringTable = StringTableMetadata


def resolve_memory_path(path: str) -> ROMRegion:
    try:
        return ASSETS.get_region(path)
    except KeyError as exc:
        raise KeyError(f"Unknown memory path: {path}") from exc


def resolve_string_table(name: str) -> StringTableMetadata:
    try:
        return ASSETS.string_tables[name]
    except KeyError as exc:
        raise KeyError(f"Unknown string table: {name}") from exc


def list_memory_paths():
    return tuple(ASSETS.regions.values())
