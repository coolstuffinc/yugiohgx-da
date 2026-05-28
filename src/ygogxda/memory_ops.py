import concurrent.futures
import csv
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .memory import MemoryEmulator, mem_region
from .registry import ASSETS, StringTableMetadata, SpriteMetadata
from .japanese_encoding import decode as japanese_decode, encode as japanese_encode
from .rom import YugiohROM
from .utils import charset_decode, rgb2gba, split_blocks, sucessive_sub


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
SUBDIR_PACKS = Path("sprites") / "card_packs"


def canonical_output_path(rom_file):
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
    if encoding == "japanese_rom":
        return japanese_encode(text)
    return text.encode(encoding)


def write_hash_manifest(directory: Path):
    hashes = {}
    for png_file in sorted(directory.glob("*.png")):
        hashes[png_file.name] = hashlib.sha256(png_file.read_bytes()).hexdigest()
    (directory / "hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    )


def dump_region(rom_file, path, output_file=None):
    if output_file is None:
        output_file = canonical_output_path(rom_file) / SUBDIR_MEMORY / f"{path}.bin"
        _ensure_output_dir(output_file.parent)
    memory = MemoryEmulator(rom_file)
    region = ASSETS.get_region(path)
    payload = memory[region.slice].read_bytes(region.size)
    with open(output_file, "wb") as output:
        output.write(payload)


def extract_sprite_resource(
    rom_file, resource_name, index, variation=0, output_file=None, rom=None
):
    if rom is None:
        rom = YugiohROM(rom_file)
    image = rom.get_sprite(resource_name, index, variation)
    if output_file is None:
        p = canonical_output_path(rom_file) / "sprites" / resource_name
        _ensure_output_dir(p)
        if resource_name == "location":
            period = LOCATION_PERIODS[variation]
            output_file = p / f"location-{period}-{index:02d}.png"
        elif resource_name == "duelist":
            output_file = p / f"duelist-{index:02d}-variation-{variation}.png"
        else:
            output_file = p / f"{resource_name}-{index:02d}.png"
    image.save(output_file)
    return output_file


def patch_sprite_resource(
    rom_file, resource_name, index, image_file, output_rom, variation=0
):
    rom = YugiohROM(rom_file)
    image = Image.open(image_file)
    rom.patch_sprite(resource_name, index, image, variation)
    rom.save(output_rom)


def extract_card_artworks(rom_file, output_dir=None, jobs=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / SUBDIR_CARDS
    output_path = _ensure_output_dir(output_dir)
    total = rom.num_cards

    def _do_one(idx):
        extract_sprite_resource(
            None,
            "card",
            idx,
            output_file=output_path / f"card-{idx:04d}.png",
            rom=rom,
        )
        return idx

    if jobs and jobs > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            for i, _ in enumerate(pool.map(_do_one, range(total))):
                if (i + 1) % 100 == 0 or i == total - 1:
                    print(f"  cards: {i + 1}/{total}", flush=True)
    else:
        for index in range(total):
            _do_one(index)
            if (index + 1) % 100 == 0 or index == total - 1:
                print(f"  cards: {index + 1}/{total}", flush=True)
    write_hash_manifest(output_path)


def extract_duelist_sprites(rom_file, output_dir=None, jobs=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / SUBDIR_DUELISTS
    output_path = _ensure_output_dir(output_dir)
    total = 29
    if jobs and jobs > 1:
        tasks = [(d, v) for d in range(total) for v in range(5)]

        def _do_one(args):
            d, v = args
            extract_sprite_resource(
                None,
                "duelist",
                d,
                v,
                output_file=output_path / f"duelist-{d:02d}-variation-{v}.png",
                rom=rom,
            )
            return d

        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            prev = -1
            for d in pool.map(_do_one, tasks):
                if d != prev:
                    print(f"  duelists: {d + 1}/{total}", flush=True)
                    prev = d
    else:
        for duelist_index in range(total):
            for variation_index in range(5):
                extract_sprite_resource(
                    None,
                    "duelist",
                    duelist_index,
                    variation_index,
                    output_file=output_path
                    / f"duelist-{duelist_index:02d}-variation-{variation_index}.png",
                    rom=rom,
                )
            print(f"  duelists: {duelist_index + 1}/29", flush=True)
    write_hash_manifest(output_path)


def extract_card_packs(rom_file, output_dir=None, jobs=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / SUBDIR_PACKS
    output_path = _ensure_output_dir(output_dir)
    total = 49

    def _do_one(idx):
        extract_sprite_resource(
            None,
            "card-pack",
            idx,
            output_file=output_path / f"card_pack-{idx:02d}.png",
            rom=rom,
        )
        return idx

    if jobs and jobs > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            for i, _ in enumerate(pool.map(_do_one, range(total))):
                if (i + 1) % 10 == 0 or i == total:
                    print(f"  card-packs: {i + 1}/{total}", flush=True)
    else:
        for index in range(total):
            _do_one(index)
            if (index + 1) % 10 == 0 or index == total - 1:
                print(f"  card-packs: {index + 1}/49", flush=True)
    write_hash_manifest(output_path)


def extract_location_thumbs(rom_file, output_dir=None, jobs=None):
    rom = YugiohROM(rom_file)
    if output_dir is None:
        output_dir = canonical_output_path(rom_file) / SUBDIR_LOCATIONS
    output_path = _ensure_output_dir(output_dir)
    total_variations = len(LOCATION_PERIODS)
    if jobs and jobs > 1:
        tasks = [
            (index, v, period)
            for v, period in enumerate(LOCATION_PERIODS)
            for index in range(26)
        ]

        def _do_one(args):
            idx, v, period = args
            extract_sprite_resource(
                None,
                "location-thumb",
                idx,
                v,
                output_file=output_path / f"location-{period}-{idx:02d}.png",
                rom=rom,
            )
            return v

        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            prev = -1
            for v in pool.map(_do_one, tasks):
                if v != prev:
                    print(
                        f"  locations: {LOCATION_PERIODS[v]} ({v + 1}/{total_variations})",
                        flush=True,
                    )
                    prev = v
    else:
        for variation, period in enumerate(LOCATION_PERIODS):
            for index in range(26):
                extract_sprite_resource(
                    None,
                    "location-thumb",
                    index,
                    variation,
                    output_file=output_path / f"location-{period}-{index:02d}.png",
                    rom=rom,
                )
            print(f"  locations: {period} ({variation + 1}/3)", flush=True)
    write_hash_manifest(output_path)


def patch_card_image(rom_file, card_id, image_file, output_rom):
    patch_sprite_resource(rom_file, "card", card_id, image_file, output_rom)


def patch_duelist_sprite(
    rom_file, duelist_index, variation_index, image_file, output_rom
):
    patch_sprite_resource(
        rom_file,
        "duelist",
        duelist_index,
        image_file,
        output_rom,
        variation=variation_index,
    )


def patch_location_thumb(rom_file, period, location_index, image_file, output_rom):
    try:
        variation = LOCATION_PERIODS.index(period)
    except ValueError:
        raise ValueError(f"period must be one of: {LOCATION_PERIODS}")
    patch_sprite_resource(
        rom_file,
        "location",
        location_index,
        image_file,
        output_rom,
        variation=variation,
    )


def patch_string_entry(rom_file, table_name, index, text, output_rom):
    memory = MemoryEmulator(rom_file)
    meta = ASSETS.string_tables[table_name]
    strings_reg = ASSETS.get_region(meta.strings_region)
    offsets_reg = ASSETS.get_region(meta.offsets_region)

    offsets_memory = memory[offsets_reg.slice]
    num_offsets = offsets_reg.size // OFFSET_SIZE
    if index < 0 or index >= num_offsets - 1:
        raise IndexError(f"index must be between 0 and {num_offsets - 2}")

    offsets = offsets_memory.read_array(num_offsets, dtype="I")
    start = strings_reg.start + int(offsets[index])
    stop = strings_reg.start + int(offsets[index + 1])
    capacity = stop - start
    if capacity <= 0:
        raise ValueError(f"Invalid table offsets for index {index}")

    encoded = _encode_string_payload(text, meta.encoding)
    if len(encoded) + 1 > capacity:
        raise ValueError(
            f"Text exceeds capacity for entry {index} (max {capacity - 1} bytes)"
        )

    patched = encoded + b"\x00" + b"\x00" * (capacity - len(encoded) - 1)
    memory[mem_region(start, capacity)] = patched
    memory.write(output_rom)


def get_string_entry(rom_file, table_name, index):
    memory = MemoryEmulator(rom_file)
    meta = ASSETS.string_tables[table_name]
    strings_reg = ASSETS.get_region(meta.strings_region)
    offsets_reg = ASSETS.get_region(meta.offsets_region)

    offsets_memory = memory[offsets_reg.slice]
    num_offsets = offsets_reg.size // OFFSET_SIZE
    if index < 0 or index >= num_offsets - 1:
        raise IndexError(f"index must be between 0 and {num_offsets - 2}")

    offsets = offsets_memory.read_array(num_offsets, dtype="I")
    start = strings_reg.start + int(offsets[index])
    stop = strings_reg.start + int(offsets[index + 1])
    payload = memory[mem_region(start, stop - start)].read_bytes(stop - start)
    return _decode_string_payload(payload, meta.encoding)


def extract_string_table(rom_file, table_name, output_file=None, index=None):
    if output_file is None and index is None:
        output_file = (
            canonical_output_path(rom_file) / SUBDIR_STRINGS / f"{table_name}.csv"
        )
        _ensure_output_dir(output_file.parent)

    memory = MemoryEmulator(rom_file)
    meta = ASSETS.string_tables[table_name]
    strings_reg = ASSETS.get_region(meta.strings_region)
    offsets_reg = ASSETS.get_region(meta.offsets_region)

    offsets_memory = memory[offsets_reg.slice]
    num_offsets = offsets_reg.size // OFFSET_SIZE
    num_entries = num_offsets - 1
    offsets = offsets_memory.read_array(num_offsets, dtype="I")

    def _read_entry(i):
        start = strings_reg.start + int(offsets[i])
        stop = strings_reg.start + int(offsets[i + 1])
        payload = memory[mem_region(start, stop - start)].read_bytes(stop - start)
        return _decode_string_payload(payload, meta.encoding)

    rows = (
        [(index, _read_entry(index))]
        if index is not None
        else [(i, _read_entry(i)) for i in range(num_entries)]
    )

    if output_file is None:
        writer = csv.writer(sys.stdout)
        writer.writerow(["index", "text"])
        writer.writerows(rows)
    else:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "text"])
            writer.writerows(rows)


def patch_string_table_bulk(rom_file, table_name, csv_file, output_rom):
    memory = MemoryEmulator(rom_file)
    meta = ASSETS.string_tables[table_name]
    strings_reg = ASSETS.get_region(meta.strings_region)
    offsets_reg = ASSETS.get_region(meta.offsets_region)

    offsets_memory = memory[offsets_reg.slice]
    num_offsets = offsets_reg.size // OFFSET_SIZE
    num_entries = num_offsets - 1
    offsets = offsets_memory.read_array(num_offsets, dtype="I")

    entries = []
    for i in range(num_entries):
        start = strings_reg.start + int(offsets[i])
        stop = strings_reg.start + int(offsets[i + 1])
        payload = memory[mem_region(start, stop - start)].read_bytes(stop - start)
        entries.append(payload.split(b"\x00", 1)[0])

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["index"])
            entries[idx] = _encode_string_payload(row["text"], meta.encoding)

    encoded = [e + b"\x00" for e in entries]
    new_total = sum(len(e) for e in encoded)
    if new_total > strings_reg.size:
        raise ValueError(
            f"Rebuilt table ({new_total} bytes) exceeds capacity ({strings_reg.size} bytes)"
        )

    new_offsets = []
    pos = 0
    for e in encoded:
        new_offsets.append(pos)
        pos += len(e)
    new_offsets.append(pos)

    memory[strings_reg.slice] = b"".join(encoded) + b"\x00" * (
        strings_reg.size - new_total
    )
    offset_bytes = np.asarray(new_offsets, dtype="<u4").tobytes()
    memory[offsets_reg.slice] = offset_bytes.ljust(offsets_reg.size, b"\x00")
    memory.write(output_rom)


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
                v = (
                    (pal_payload[bank_idx * 2] | (pal_payload[bank_idx * 2 + 1] << 8))
                    if bank_idx < pal_n
                    else 0x7C1F
                )
                pal.extend([v & 0xFF, (v >> 8) & 0xFF])
            img = Image.fromarray(arr)
            img.putpalette(pal, rawmode="RGB;15")
            img.save(output_path / f"card_pile_{idx}_bank{bank}.png")
    write_hash_manifest(output_path)
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
            raise FileNotFoundError(f"No layers for card_pile_{idx} in {layers_dir}")
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
TRAP_SUBTYPE_NAMES = {0: {0: "Normal Trap", 1: "Counter Trap"}, 2: "Continuous Trap"}


def decode_card_stats(val):
    if val == 0:
        return {"category": "Empty/Unused"}
    b0_8, b9_17, b18_19, b20_24, b25_28, b29_31 = (
        val & 0x1FF,
        (val >> 9) & 0x1FF,
        (val >> 18) & 3,
        (val >> 20) & 0x1F,
        (val >> 25) & 0xF,
        (val >> 29) & 7,
    )
    if b20_24 == 22:
        st = SPELL_SUBTYPE_NAMES.get(b18_19, f"Unknown({b18_19})")
        if isinstance(st, dict):
            st = st.get((val >> 17) & 1, f"Unknown({b18_19},{(val >> 17) & 1})")
        return {"category": "Spell", "subtype": st}
    elif b20_24 == 21:
        st = TRAP_SUBTYPE_NAMES.get(b18_19, f"Unknown({b18_19})")
        if isinstance(st, dict):
            st = st.get((val >> 17) & 1, f"Unknown({b18_19},{(val >> 17) & 1})")
        return {"category": "Trap", "subtype": st}
    return {
        "category": "Monster",
        "subtype": CARD_CATEGORY_NAMES.get(b18_19, f"Unknown({b18_19})"),
        "type": MONSTER_TYPE_NAMES.get(b20_24, f"Unknown({b20_24})"),
        "attribute": ATTRIBUTE_NAMES.get(b29_31, f"Unknown({b29_31})"),
        "level": b25_28,
        "atk": b9_17 * 10,
        "def": b0_8 * 10,
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
    LUT = rom.rom[rom.CARD_NUMBER_TO_ID].read_array(1201, dtype="H")
    if password is not None:
        ordinal = rom.passwords.enter(password)
        if ordinal == 0:
            raise ValueError(f"Invalid password: {password}")
    if ordinal is not None:
        if ordinal < 0 or ordinal >= 1201:
            raise ValueError(f"Ordinal out of range: {ordinal}")
        cid, pwd, name = (
            int(LUT[ordinal]),
            rom.passwords.unlock(ordinal),
            rom.card_names[ordinal],
        )
        text = rom.card_texts[ordinal] if show_text else None
    elif card_id is not None:
        matches = [i for i in range(1201) if LUT[i] == card_id]
        if not matches:
            raise ValueError(f"No card found with card_id {card_id}")
        ordinal = matches[0]
        cid, pwd, name = card_id, rom.passwords.unlock(ordinal), rom.card_names[ordinal]
        text = rom.card_texts[ordinal] if show_text else None
    else:
        raise ValueError("Provide one of: --ordinal, --card-id, --password")
    stats = (
        decode_card_stats(rom.rom[rom.CARD_STATS].read_array(1201, dtype="I")[ordinal])
        if show_stats
        else None
    )
    return {
        "ordinal": ordinal,
        "card_id": cid,
        "name": name,
        "password": pwd,
        "text": text,
        "stats": stats,
    }


def encode_card_stats(current=None, **overrides):
    val = current if current is not None else 0
    b0_8, b9_17, b18_19, b20_24, b25_28, b29_31 = (
        val & 0x1FF,
        (val >> 9) & 0x1FF,
        (val >> 18) & 3,
        (val >> 20) & 0x1F,
        (val >> 25) & 0xF,
        (val >> 29) & 7,
    )
    c = overrides.get("category")
    if c:
        k = c.lower().split()[0]
        if b20_24 == 22 or c.lower() in (
            "normal spell",
            "field spell",
            "equip spell",
            "continuous spell",
            "quick-play spell",
            "ritual spell",
        ):
            b18_19 = SPELL_SUBTYPE_NAMES.get(k, b18_19)
        else:
            b18_19 = CARD_CATEGORY_IDS.get(k, b18_19)
    if "type" in overrides:
        b20_24 = MONSTER_TYPE_IDS.get(overrides["type"].lower(), b20_24)
    if "attribute" in overrides:
        b29_31 = ATTRIBUTE_IDS.get(overrides["attribute"].lower(), b29_31)
    if "level" in overrides:
        b25_28 = int(overrides["level"]) & 0xF
    if "atk" in overrides:
        b9_17 = (int(overrides["atk"]) // 10) & 0x1FF
    if "def" in overrides:
        b0_8 = (int(overrides["def"]) // 10) & 0x1FF
    return (
        (b29_31 << 29)
        | (b25_28 << 25)
        | (b20_24 << 20)
        | (b18_19 << 18)
        | (b9_17 << 9)
        | b0_8
    )


def patch_card_stats(rom_file, ordinal, output_file, **overrides):
    rom = YugiohROM(rom_file)
    offset = rom.CARD_STATS.start + ordinal * 4
    current = rom.rom.read_struct("<I", offset=offset)
    new_val = encode_card_stats(current=int(current), **overrides)
    rom.rom[mem_region(offset, 4)] = struct.pack("<I", new_val)
    rom.save(output_file)
    return new_val
