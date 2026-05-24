from pathlib import Path

import numpy as np
from PIL import Image

from .memory import MemoryEmulator, mem_region
from .memory_map import list_memory_paths, resolve_memory_path, resolve_string_table
from .rom import YugiohROM
from .utils import split_blocks


CARD_IMAGE_SIDE = 80
CARD_IMAGE_SIZE = CARD_IMAGE_SIDE * CARD_IMAGE_SIDE
OFFSET_SIZE = 4
LOCATION_PERIODS = ("morning", "afternoon", "night")


def _ensure_output_dir(output_dir):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def dump_region(rom_file, path, output_file):
    memory = MemoryEmulator(rom_file)
    region = resolve_memory_path(path).region
    payload = memory[region].read_bytes(region.stop - region.start)
    with open(output_file, "wb") as output:
        output.write(payload)


def patch_card_image(rom_file, card_id, image_file, output_rom):
    memory = MemoryEmulator(rom_file)
    bitmap_path = resolve_memory_path("cards.high_res.bitmaps")
    num_cards = bitmap_path.size // CARD_IMAGE_SIZE
    if card_id < 0 or card_id >= num_cards:
        raise ValueError(f"card_id must be between 0 and {num_cards - 1}")

    image = Image.open(image_file).convert("L")
    if image.size != (CARD_IMAGE_SIDE, CARD_IMAGE_SIDE):
        image = image.resize((CARD_IMAGE_SIDE, CARD_IMAGE_SIDE), Image.Resampling.NEAREST)
    pixels = np.asarray(image, dtype=np.uint8).reshape(CARD_IMAGE_SIDE, CARD_IMAGE_SIDE)
    blocked_pixels = split_blocks(pixels, (10, 10)).flatten().astype(np.uint8).tobytes()

    start = bitmap_path.region.start + card_id * CARD_IMAGE_SIZE
    region = mem_region(start, CARD_IMAGE_SIZE)
    memory[region] = blocked_pixels
    memory.write(output_rom)


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
    return payload.split(b"\x00", 1)[0].decode(table.encoding)
