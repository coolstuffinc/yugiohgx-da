import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .memory import MemoryEmulator, mem_region
from .memory_map import CANONICAL_STRING_TABLES, list_memory_paths, resolve_memory_path, resolve_string_table
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
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError:
        try:
            return charset_decode(raw)
        except UnicodeDecodeError:
            return raw.decode(encoding, errors="replace")


def dump_region(rom_file, path, output_file):
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
    _patch_indexed_image(bitmap_region, palette_region, pixels, palette, CARD_IMAGE_BLOCKS)
    rom.patch(bitmap_region)
    rom.patch(palette_region)
    rom.save(output_rom)


def extract_card_artworks(rom_file, output_dir):
    rom = YugiohROM(rom_file)
    output_path = _ensure_output_dir(output_dir)
    for index, artwork in enumerate(rom.card_images):
        artwork.save(output_path / f"card-{index:04d}.png")


def extract_duelist_sprites(rom_file, output_dir):
    rom = YugiohROM(rom_file)
    output_path = _ensure_output_dir(output_dir)
    for duelist_index, variations in enumerate(rom.duelist_sprites()):
        for variation_index, image in enumerate(variations):
            image.save(output_path / f"duelist-{duelist_index:02d}-variation-{variation_index}.png")


def extract_location_thumbs(rom_file, output_dir):
    rom = YugiohROM(rom_file)
    output_path = _ensure_output_dir(output_dir)
    for period, images in zip(LOCATION_PERIODS, rom.location_thumbs()):
        for location_index, image in enumerate(images):
            image.save(output_path / f"location-{period}-{location_index:02d}.png")


def patch_duelist_sprite(rom_file, duelist_index, variation_index, image_file, output_rom):
    rom = YugiohROM(rom_file)
    pixels, palette = _load_indexed_image(
        image_file, DUELIST_SPRITE_SIZE, DUELIST_SPRITE_PALETTE_COLORS
    )
    bitmap_region = rom.duelist_sprite_bitmap(duelist_index, variation_index)
    palette_region = rom.duelist_sprite_palette(duelist_index)
    _patch_indexed_image(bitmap_region, palette_region, pixels, palette, DUELIST_SPRITE_BLOCKS)
    rom.patch(bitmap_region)
    rom.patch(palette_region)
    rom.save(output_rom)


def patch_location_thumb(rom_file, period, location_index, image_file, output_rom):
    rom = YugiohROM(rom_file)
    try:
        period_index = LOCATION_PERIODS.index(period)
    except ValueError as exc:
        raise ValueError(f"period must be one of: {', '.join(LOCATION_PERIODS)}") from exc

    pixels, palette = _load_indexed_image(
        image_file, LOCATION_THUMB_SIZE, LOCATION_THUMB_PALETTE_COLORS
    )
    bitmap_region = rom.location_thumb_bitmap(period_index, location_index)
    palette_region = rom.location_thumb_palette(period_index, location_index)
    _patch_indexed_image(bitmap_region, palette_region, pixels, palette, LOCATION_THUMB_BLOCKS)
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

    encoded = text.encode(table.encoding)
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

    Writes to *output_file* when provided, otherwise to stdout.  Pass *index*
    to restrict output to a single entry (requires *table_name*).
    """
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
            entries[idx] = row["text"].encode(table.encoding)

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
