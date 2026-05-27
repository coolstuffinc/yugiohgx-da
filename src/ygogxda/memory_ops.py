import csv
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .memory import MemoryEmulator, mem_region
from .memory_map import (
    CANONICAL_STRING_TABLES,
    list_memory_paths,
    resolve_memory_path,
    resolve_string_table,
)
from .japanese_encoding import decode as japanese_decode, encode as japanese_encode
from .rom import YugiohROM
from .utils import charset_decode, rgb2gba, split_blocks


CARD_IMAGE_SIDE = 80
CARD_IMAGE_SIZE = CARD_IMAGE_SIDE * CARD_IMAGE_SIDE
CARD_IMAGE_BLOCKS = (10, 10)
CARD_IMAGE_PALETTE_COLORS = 64
OFFSET_SIZE = 4
LOCATION_PERIODS = ("morning", "afternoon", "night")
DUELIST_SPRITE_SIZE = (64, 64)
DUELIST_SPRITE_BLOCKS = (8, 8)
DUELIST_SPRITE_PALETTE_COLORS = 64
LOCATION_THUMB_SIZE = (96, 64)
LOCATION_THUMB_BLOCKS = (12, 8)
LOCATION_THUMB_PALETTE_COLORS = 64

SUBDIR_CARDS = Path("sprites") / "cards"
SUBDIR_DUELISTS = Path("sprites") / "duelists"
SUBDIR_LOCATIONS = Path("sprites") / "locations" / "thumbs"
SUBDIR_STRINGS = Path("strings")
SUBDIR_MEMORY = Path("memory")


def canonical_output_path(rom_file):
    """Return the canonical extraction directory for a ROM file.

    Given ``rom_file`` (e.g. ``ygogxda.gba``), returns
    ``ygogxda.gba.extracted/`` next to the ROM file.
    """
    p = Path(rom_file)
    return p.with_name(p.name + ".extracted")


def _ensure_output_dir(output_dir):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _convert_palette_to_gba(image, palette_entries):
    palette = (image.getpalette() or [])[: palette_entries * 3]
    palette += [0] * (palette_entries * 3 - len(palette))
    colors = np.asarray(palette, dtype=np.uint8).reshape(palette_entries, 3)
    gba_palette = np.asarray(
        [rgb2gba(int(red), int(green), int(blue)) for red, green, blue in colors],
        dtype="<u2",
    )
    return gba_palette.tobytes()


def _quantize_image(image, palette_entries):
    return image.convert("RGB").quantize(colors=palette_entries)


def _load_indexed_image(image_file, size, palette_entries):
    image_path = Path(image_file)
    if not image_path.is_file():
        raise FileNotFoundError(f"Input image file does not exist: {image_file}")

    image = Image.open(image_file)
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)

    indexed = image if image.mode == "P" else _quantize_image(image, palette_entries)

    pixels = np.asarray(indexed, dtype=np.uint8)
    max_index = int(pixels.max())
    if max_index >= palette_entries:
        indexed = _quantize_image(indexed, palette_entries)
        pixels = np.asarray(indexed, dtype=np.uint8)

    return pixels, _convert_palette_to_gba(indexed, palette_entries)


def _patch_indexed_image(bitmap_region, palette_region, pixels, palette_bytes, blocks):
    bitmap_region[:] = split_blocks(pixels, blocks).flatten().tobytes()
    palette_region[:] = palette_bytes


def _decode_string_payload(payload, encoding):
    """Decode a null-terminated string payload with compatibility fallbacks."""
    raw = payload.split(b"\x00", 1)[0]
    if encoding == "japanese_rom":
        return japanese_decode(raw)
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        try:
            return charset_decode(raw)
        except UnicodeDecodeError:
            try:
                return raw.decode(encoding, errors="replace")
            except LookupError:
                return raw.decode("latin-1", errors="replace")


def _encode_string_payload(text, encoding):
    """Encode text for a table-specific encoding."""
    if encoding == "japanese_rom":
        return japanese_encode(text)
    return text.encode(encoding)


def dump_region(rom_file, path, output_file=None):
    if output_file is None:
        output_file = canonical_output_path(rom_file) / SUBDIR_MEMORY / f"{path}.bin"
        _ensure_output_dir(output_file.parent)
    memory = MemoryEmulator(rom_file)
    region = resolve_memory_path(path).region
    payload = memory[region].read_bytes(region.stop - region.start)
    with open(output_file, "wb") as output:
        output.write(payload)


def patch_card_image(rom_file, card_id, image_file, output_rom):
    rom = YugiohROM(rom_file)
    pixels, palette = _load_indexed_image(
        image_file,
        (CARD_IMAGE_SIDE, CARD_IMAGE_SIDE),
        CARD_IMAGE_PALETTE_COLORS,
    )
    bitmap_region = rom.card_artwork_bitmap(card_id)
    palette_region = rom.card_artwork_palette(card_id)
    _patch_indexed_image(
        bitmap_region, palette_region, pixels, palette, CARD_IMAGE_BLOCKS
    )
    rom.patch(bitmap_region)
    rom.patch(palette_region)
    rom.save(output_rom)


def extract_card_artworks(rom_file, output_dir=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / SUBDIR_CARDS
    output_path = _ensure_output_dir(output_dir)
    for index, artwork in enumerate(rom.card_images):
        artwork.save(output_path / f"card-{index:04d}.png")


def extract_duelist_sprites(rom_file, output_dir=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / SUBDIR_DUELISTS
    output_path = _ensure_output_dir(output_dir)
    for duelist_index, variations in enumerate(rom.duelist_sprites()):
        for variation_index, image in enumerate(variations):
            image.save(
                output_path
                / f"duelist-{duelist_index:02d}-variation-{variation_index}.png"
            )


def extract_location_thumbs(rom_file, output_dir=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / SUBDIR_LOCATIONS
    output_path = _ensure_output_dir(output_dir)
    for period, images in zip(LOCATION_PERIODS, rom.location_thumbs()):
        for location_index, image in enumerate(images):
            image.save(output_path / f"location-{period}-{location_index:02d}.png")


def patch_duelist_sprite(
    rom_file, duelist_index, variation_index, image_file, output_rom
):
    rom = YugiohROM(rom_file)
    pixels, palette = _load_indexed_image(
        image_file, DUELIST_SPRITE_SIZE, DUELIST_SPRITE_PALETTE_COLORS
    )
    bitmap_region = rom.duelist_sprite_bitmap(duelist_index, variation_index)
    palette_region = rom.duelist_sprite_palette(duelist_index)
    _patch_indexed_image(
        bitmap_region, palette_region, pixels, palette, DUELIST_SPRITE_BLOCKS
    )
    rom.patch(bitmap_region)
    rom.patch(palette_region)
    rom.save(output_rom)


def patch_location_thumb(rom_file, period, location_index, image_file, output_rom):
    rom = YugiohROM(rom_file)
    try:
        period_index = LOCATION_PERIODS.index(period)
    except ValueError as exc:
        raise ValueError(
            f"period must be one of: {', '.join(LOCATION_PERIODS)}"
        ) from exc

    pixels, palette = _load_indexed_image(
        image_file, LOCATION_THUMB_SIZE, LOCATION_THUMB_PALETTE_COLORS
    )
    bitmap_region = rom.location_thumb_bitmap(period_index, location_index)
    palette_region = rom.location_thumb_palette(period_index, location_index)
    _patch_indexed_image(
        bitmap_region, palette_region, pixels, palette, LOCATION_THUMB_BLOCKS
    )
    rom.patch(bitmap_region)
    rom.patch(palette_region)
    rom.save(output_rom)


def patch_string_entry(rom_file, table_name, index, text, output_rom):
    memory = MemoryEmulator(rom_file)
    table = resolve_string_table(table_name)
    strings_region = resolve_memory_path(table.strings_path).region
    offsets_region = resolve_memory_path(table.offsets_path).region

    offsets_memory = memory[offsets_region]
    num_offsets = len(offsets_memory) // OFFSET_SIZE
    if index < 0 or index >= num_offsets - 1:
        raise IndexError(f"index must be between 0 and {num_offsets - 2}")

    offsets = offsets_memory.read_array(num_offsets, dtype="I")
    start = strings_region.start + int(offsets[index])
    stop = strings_region.start + int(offsets[index + 1])
    capacity = stop - start
    if capacity <= 0:
        raise ValueError(f"Invalid table offsets for index {index}")

    encoded = _encode_string_payload(text, table.encoding)
    if len(encoded) + 1 > capacity:
        raise ValueError(
            f"Text exceeds capacity for entry {index} in {table_name} "
            f"(maximum {capacity - 1} bytes)"
        )

    patched = encoded + b"\x00" + b"\x00" * (capacity - len(encoded) - 1)
    memory[mem_region(start, capacity)] = patched
    memory.write(output_rom)


def get_string_entry(rom_file, table_name, index):
    memory = MemoryEmulator(rom_file)
    table = resolve_string_table(table_name)
    strings_region = resolve_memory_path(table.strings_path).region
    offsets_region = resolve_memory_path(table.offsets_path).region

    offsets_memory = memory[offsets_region]
    num_offsets = len(offsets_memory) // OFFSET_SIZE
    if index < 0 or index >= num_offsets - 1:
        raise IndexError(f"index must be between 0 and {num_offsets - 2}")

    offsets = offsets_memory.read_array(num_offsets, dtype="I")
    start = strings_region.start + int(offsets[index])
    stop = strings_region.start + int(offsets[index + 1])
    payload = memory[mem_region(start, stop - start)].read_bytes(stop - start)
    return _decode_string_payload(payload, table.encoding)


def extract_string_table(rom_file, table_name, output_file=None, index=None):
    """Extract string table entries to CSV.

    Writes to *output_file* when provided.  When *output_file* is ``None`` and
    *index* is also ``None``, writes to the canonical path
    ``<rom>.extracted/strings/<table_name>.csv``.  When *output_file* is
    ``None`` but *index* is given, writes to stdout.
    """
    if output_file is None and index is None:
        output_file = (
            canonical_output_path(rom_file) / SUBDIR_STRINGS / f"{table_name}.csv"
        )
        _ensure_output_dir(output_file.parent)
    memory = MemoryEmulator(rom_file)
    table = resolve_string_table(table_name)
    strings_region = resolve_memory_path(table.strings_path).region
    offsets_region = resolve_memory_path(table.offsets_path).region

    offsets_memory = memory[offsets_region]
    num_offsets = len(offsets_memory) // OFFSET_SIZE
    num_entries = num_offsets - 1
    offsets = offsets_memory.read_array(num_offsets, dtype="I")

    def _read_entry(i):
        start = strings_region.start + int(offsets[i])
        stop = strings_region.start + int(offsets[i + 1])
        payload = memory[mem_region(start, stop - start)].read_bytes(stop - start)
        return _decode_string_payload(payload, table.encoding)

    if index is not None:
        if index < 0 or index >= num_entries:
            raise IndexError(f"index must be between 0 and {num_entries - 1}")
        rows = [(index, _read_entry(index))]
    else:
        rows = [(i, _read_entry(i)) for i in range(num_entries)]

    if output_file is None:
        writer = csv.writer(sys.stdout)
        writer.writerow(["index", "text"])
        writer.writerows(rows)
    else:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "text"])
            writer.writerows(rows)


CARD_PILE_CANONICAL_SUBDIR = Path("sprites") / "card_piles"


def extract_card_pile_layers(rom_file, index=None, output_dir=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / CARD_PILE_CANONICAL_SUBDIR
    output_path = _ensure_output_dir(output_dir)

    indices = range(8) if index is None else [index]
    for idx in indices:
        composite = rom.card_pile_background(idx)
        composite.save(output_path / f"card_pile_{idx}_composite.png")

        layers, pal_n, pal_payload = rom.card_pile_background_layers(idx)
        for bank, arr in layers.items():
            pal = bytearray()
            for j in range(16):
                bank_idx = bank * 16 + j
                if bank_idx < pal_n:
                    v = pal_payload[bank_idx * 2] | (pal_payload[bank_idx * 2 + 1] << 8)
                else:
                    v = 0x7C1F
                pal.extend([v & 0xFF, (v >> 8) & 0xFF])
            img = Image.fromarray(arr)
            img.putpalette(pal, rawmode="RGB;15")
            img.save(output_path / f"card_pile_{idx}_bank{bank}.png")

    return output_path


def patch_card_pile_background_from_files(
    rom_file, index=None, layers_dir=None, output_rom=None
):
    if layers_dir is None:
        layers_dir = canonical_output_path(rom_file) / CARD_PILE_CANONICAL_SUBDIR
    layers_path = Path(layers_dir)
    rom = YugiohROM(rom_file)

    indices = range(8) if index is None else [index]
    for idx in indices:
        _, pal_n, pal_payload = rom.card_pile_background_layers(idx)
        layers = {}
        for bank in sorted({0, 1, 2}):
            png = layers_path / f"card_pile_{idx}_bank{bank}.png"
            if png.is_file():
                img = Image.open(png)
                arr = np.asarray(img, dtype=np.uint8)
                if arr.shape != (160, 240):
                    arr = np.asarray(
                        img.resize((240, 160), Image.Resampling.NEAREST), dtype=np.uint8
                    )
                layers[bank] = arr
        if not layers:
            raise FileNotFoundError(
                f"No layer PNGs found for card_pile_{idx} in {layers_dir}"
            )
        rom.patch_card_pile_background(idx, layers)

    rom.save(output_rom)


MONSTER_TYPE_NAMES = {
    1: "Dragon",
    2: "Zombie",
    3: "Fiend",
    4: "Pyro",
    5: "Sea Serpent",
    6: "Rock",
    7: "Machine",
    8: "Fish",
    9: "Dinosaur",
    10: "Insect",
    11: "Beast",
    12: "Beast-Warrior",
    13: "Plant",
    14: "Aqua",
    15: "Warrior",
    16: "Winged Beast",
    17: "Fairy",
    18: "Spellcaster",
    19: "Thunder",
    20: "Reptile",
}

MONSTER_TYPE_IDS = {v.lower(): k for k, v in MONSTER_TYPE_NAMES.items()}

ATTRIBUTE_NAMES = {1: "LIGHT", 2: "DARK", 3: "WATER", 4: "FIRE", 5: "EARTH", 6: "WIND"}
ATTRIBUTE_IDS = {v.lower(): k for k, v in ATTRIBUTE_NAMES.items()}

CARD_CATEGORY_NAMES = {
    0: "Normal Monster",
    1: "Effect Monster",
    2: "Fusion Monster",
    3: "Ritual Monster",
}
CARD_CATEGORY_IDS = {v.lower().split()[0]: k for k, v in CARD_CATEGORY_NAMES.items()}

SPELL_SUBTYPE_NAMES = {
    0: "Normal Spell",
    1: {0: "Field Spell", 1: "Equip Spell"},
    2: {0: "Continuous Spell", 1: "Quick-Play Spell"},
    3: "Ritual Spell",
}

TRAP_SUBTYPE_NAMES = {
    0: {0: "Normal Trap", 1: "Counter Trap"},
    2: "Continuous Trap",
}


def decode_card_stats(val):
    """Decode a 32-bit card stats value into a human-readable dict."""
    if val == 0:
        return {"category": "Empty/Unused"}
    b0_8 = val & 0x1FF
    b9_17 = (val >> 9) & 0x1FF
    b18_19 = (val >> 18) & 3
    b20_24 = (val >> 20) & 0x1F
    b25_28 = (val >> 25) & 0xF
    b29_31 = (val >> 29) & 7

    if b20_24 == 22:
        # Spell card
        subtype = SPELL_SUBTYPE_NAMES.get(b18_19, f"Unknown({b18_19})")
        if isinstance(subtype, dict):
            bit17 = (val >> 17) & 1
            subtype = subtype.get(bit17, f"Unknown({b18_19},{bit17})")
        return {"category": "Spell", "subtype": subtype}
    elif b20_24 == 21:
        # Trap card
        subtype = TRAP_SUBTYPE_NAMES.get(b18_19, f"Unknown({b18_19})")
        if isinstance(subtype, dict):
            bit17 = (val >> 17) & 1
            subtype = subtype.get(bit17, f"Unknown({b18_19},{bit17})")
        return {"category": "Trap", "subtype": subtype}
    else:
        # Monster card
        atk = b9_17 * 10
        defense = b0_8 * 10
        level = b25_28
        attr = ATTRIBUTE_NAMES.get(b29_31, f"Unknown({b29_31})")
        mtype = MONSTER_TYPE_NAMES.get(b20_24, f"Unknown({b20_24})")
        cat = CARD_CATEGORY_NAMES.get(b18_19, f"Unknown({b18_19})")
        return {
            "category": "Monster",
            "subtype": cat,
            "type": mtype,
            "attribute": attr,
            "level": level,
            "atk": atk,
            "def": defense,
        }


def lookup_card(
    rom_file,
    ordinal=None,
    card_id=None,
    password=None,
    show_text=False,
    show_stats=False,
):
    rom = YugiohROM(rom_file)
    LUT = rom.rom[YugiohROM.CARD_NUMBER_TO_ID].read_array(1201, dtype="H")

    if password is not None:
        ordinal = rom.passwords.enter(password)
        if ordinal == 0:
            raise ValueError(f"Invalid password: {password}")

    if ordinal is not None:
        if ordinal < 0 or ordinal >= 1201:
            raise ValueError(f"Ordinal must be 0..1200, got {ordinal}")
        cid = int(LUT[ordinal])
        pwd = rom.passwords.unlock(ordinal)
        name = rom.card_names[ordinal]
        text = rom.card_texts[ordinal] if show_text else None
    elif card_id is not None:
        matches = [i for i in range(1201) if LUT[i] == card_id]
        if not matches:
            raise ValueError(f"No card found with card_id {card_id}")
        ordinal = matches[0]
        cid = card_id
        pwd = rom.passwords.unlock(ordinal)
        name = rom.card_names[ordinal]
        text = rom.card_texts[ordinal] if show_text else None
    else:
        raise ValueError("Provide one of: --ordinal, --card-id, --password")

    stats_val = rom.rom[YugiohROM.CARD_STATS].read_array(1201, dtype="I")[ordinal]
    stats = decode_card_stats(stats_val)

    return {
        "ordinal": ordinal,
        "card_id": cid,
        "name": name,
        "password": pwd,
        "text": text,
        "stats": stats if show_stats else None,
    }


def encode_card_stats(current=None, **overrides):
    """Build a 32-bit card stats value from keyword overrides.

    Accepts: category, type, attribute, level, atk, defense, subtype.
    If *current* is given (int), it's used as a base and only specified
    fields are changed.  Otherwise the value is built from scratch.
    """
    if current is not None:
        val = current
    else:
        val = 0

    b0_8 = val & 0x1FF
    b9_17 = (val >> 9) & 0x1FF
    b18_19 = (val >> 18) & 3
    b20_24 = (val >> 20) & 0x1F
    b25_28 = (val >> 25) & 0xF
    b29_31 = (val >> 29) & 7

    cat_str = overrides.get("category")
    if cat_str is not None:
        key = cat_str.lower().split()[0]
        if b20_24 == 22 or cat_str.lower() in (
            "normal spell",
            "field spell",
            "equip spell",
            "continuous spell",
            "quick-play spell",
            "ritual spell",
        ):
            b18_19 = SPELL_SUBTYPE_NAMES.get(key)
        else:
            b18_19 = CARD_CATEGORY_IDS.get(key, b18_19)
        if b18_19 is None and cat_str.isdigit():
            b18_19 = int(cat_str) & 3

    mtype_str = overrides.get("type")
    if mtype_str is not None:
        b20_24 = MONSTER_TYPE_IDS.get(mtype_str.lower(), b20_24)
        if b20_24 is None or (isinstance(b20_24, str) and b20_24.isdigit()):
            b20_24 = int(mtype_str) & 0x1F

    attr_str = overrides.get("attribute")
    if attr_str is not None:
        b29_31 = ATTRIBUTE_IDS.get(attr_str.lower(), b29_31)
        if b29_31 is None or (isinstance(b29_31, str) and b29_31.isdigit()):
            b29_31 = int(attr_str) & 7

    level = overrides.get("level")
    if level is not None:
        b25_28 = int(level) & 0xF

    atk = overrides.get("atk")
    if atk is not None:
        b9_17 = (int(atk) // 10) & 0x1FF

    defense = overrides.get("def")
    if defense is not None:
        b0_8 = (int(defense) // 10) & 0x1FF

    return (
        (b29_31 << 29)
        | (b25_28 << 25)
        | (b20_24 << 20)
        | (b18_19 << 18)
        | (b9_17 << 9)
        | b0_8
    )


def patch_card_stats(rom_file, ordinal, output_file, **overrides):
    """Read one card's stat entry, apply overrides, write to output ROM."""
    memory = MemoryEmulator(rom_file)
    base = YugiohROM.CARD_STATS.start
    offset = base + ordinal * 4
    current = memory.read_struct("<I", offset=offset)
    new_val = encode_card_stats(current=int(current), **overrides)
    memory[mem_region(offset, 4)] = struct.pack("<I", new_val)
    memory.write(output_file)
    return new_val


def patch_string_table_bulk(rom_file, table_name, csv_file, output_rom):
    """Patch multiple string table entries from a CSV, rebuilding the offset table.

    The CSV must have *index* and *text* columns.  Only listed entries are
    modified; all others keep their current values.  Offsets are regenerated
    from scratch so entries may borrow space from each other as long as the
    total encoded size (including null terminators) fits inside the original
    string region.
    """
    memory = MemoryEmulator(rom_file)
    table = resolve_string_table(table_name)
    strings_path_obj = resolve_memory_path(table.strings_path)
    strings_region = strings_path_obj.region
    offsets_region = resolve_memory_path(table.offsets_path).region
    region_capacity = strings_path_obj.size

    offsets_memory = memory[offsets_region]
    num_offsets = len(offsets_memory) // OFFSET_SIZE
    num_entries = num_offsets - 1
    offsets = offsets_memory.read_array(num_offsets, dtype="I")

    # Read all current entries
    entries = []
    for i in range(num_entries):
        start = strings_region.start + int(offsets[i])
        stop = strings_region.start + int(offsets[i + 1])
        payload = memory[mem_region(start, stop - start)].read_bytes(stop - start)
        entries.append(payload.split(b"\x00", 1)[0])

    # Apply CSV overrides
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["index"])
            if idx < 0 or idx >= num_entries:
                raise IndexError(f"CSV index {idx} out of range 0..{num_entries - 1}")
            entries[idx] = _encode_string_payload(row["text"], table.encoding)

    # Encode all entries (null-terminated)
    encoded = [entry + b"\x00" for entry in entries]
    new_total = sum(len(e) for e in encoded)
    if new_total > region_capacity:
        raise ValueError(
            f"Rebuilt string table ({new_total} bytes) exceeds region capacity ({region_capacity} bytes)"
        )

    # Rebuild offsets
    new_offsets = []
    pos = 0
    for e in encoded:
        new_offsets.append(pos)
        pos += len(e)
    new_offsets.append(pos)  # sentinel

    # Write blob padded to original region size, then the new offset table
    blob = b"".join(encoded) + b"\x00" * (region_capacity - new_total)
    memory[strings_region] = blob
    memory[offsets_region] = np.asarray(new_offsets, dtype="<u4").tobytes()
    memory.write(output_rom)
