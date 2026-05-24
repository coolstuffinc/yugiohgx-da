import os
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ygogxda.cli import build_parser
from ygogxda.memory import MemoryEmulator
from ygogxda.passwords import YugiohPasswords
from ygogxda.memory_map import list_memory_paths
from ygogxda.memory_ops import (
    DUELIST_SPRITE_BLOCKS,
    LOCATION_THUMB_BLOCKS,
    extract_card_artworks,
    extract_duelist_sprites,
    extract_location_thumbs,
    get_string_entry,
    patch_card_image,
    patch_duelist_sprite,
    patch_location_thumb,
    patch_string_entry,
)
from ygogxda.rom import YugiohROM
from ygogxda.utils import rgb2gba, split_blocks


def write_bytes(payload, real_address, data):
    start = real_address - 0x08000000
    payload[start:start + len(data)] = data


def write_u16(payload, real_address, value):
    write_bytes(payload, real_address, struct.pack("<H", value))


def write_u32(payload, real_address, value):
    write_bytes(payload, real_address, struct.pack("<I", value))


def build_synthetic_rom():
    required_stops = [
        YugiohROM.CARD_HIGH_RES_BITMAPS.stop,
        YugiohROM.CARD_HIGH_RES_PALETTES.stop,
        YugiohROM.CHARACTERS_BITMAPS.stop,
        YugiohROM.CHARACTERS_PALETTES.stop,
        YugiohROM.ACADEMY_LOCATIONS_THUMBS.stop,
        YugiohROM.CARD_NAMES_OFFSETS_EN.stop,
        YugiohROM.CARD_TEXTS_OFFSETS_EN.stop,
        YugiohROM.CARD_PASSWORD_KEYS.stop,
        YugiohROM.CARD_NUMBER_TO_ID.stop,
    ]
    payload = bytearray(max(required_stops) - 0x08000000)

    header = struct.pack(
        "<I156s12s4s2s1b1b1b7s1b1b2s",
        0xEA00002E,
        b"\x00" * 156,
        b"YUGIOHGXDA\x00\x00",
        b"BYGE",
        b"01",
        0,
        0,
        0,
        b"\x00" * 7,
        0,
        0,
        b"\x00\x00",
    )
    write_bytes(payload, 0x08000000, header)
    write_u32(payload, YugiohROM.CARD_TOTAL_NUMBER.start, 3)

    for i in range(1201):
        write_u32(payload, YugiohROM.CARD_NAMES_OFFSETS_EN.start + i * 4, i * 2)
        write_u32(payload, YugiohROM.CARD_TEXTS_OFFSETS_EN.start + i * 4, i * 3)
        write_u16(payload, YugiohROM.CARD_NUMBER_TO_ID.start + i * 2, i)

    names_data = bytearray()
    texts_data = bytearray()
    for i in range(1200):
        names_data.extend(bytes([ord("A") + (i % 26), 0]))
        texts_data.extend(bytes([ord("a") + (i % 26), ord("!"), 0]))
    write_bytes(payload, YugiohROM.CARD_NAMES_EN.start, names_data)
    write_bytes(payload, YugiohROM.CARD_TEXTS_EN.start, texts_data)

    password = "12345678"
    hashed = YugiohPasswords.forward_hash(bytes(int(ch) for ch in password))
    key = hashed ^ YugiohPasswords.padding(1)
    write_u32(payload, YugiohROM.CARD_PASSWORD_KEYS.start + 4, key)

    duelists_table = YugiohROM.CHARACTERS_BITMAPS.start + 29 * 4
    duelists_bitmaps = duelists_table + 5 * 4
    for index in range(29):
        write_u32(payload, YugiohROM.CHARACTERS_BITMAPS.start + index * 4, duelists_table)
        write_u32(payload, YugiohROM.CHARACTERS_PALETTES.start + index * 4, YugiohROM.CHARACTERS_PALETTES.start + 29 * 4)
    for variation in range(5):
        write_u32(payload, duelists_table + variation * 4, duelists_bitmaps + variation * 4096)

    locations_bitmap_table = YugiohROM.ACADEMY_LOCATIONS_THUMBS.start + 24
    locations_palette_table = locations_bitmap_table + 26 * 4
    locations_bitmap_data = locations_palette_table + 26 * 4
    locations_palette_data = locations_bitmap_data + 26 * (4 + 6144)
    for period in range(3):
        write_u32(payload, YugiohROM.ACADEMY_LOCATIONS_THUMBS.start + period * 4, locations_bitmap_table)
        write_u32(payload, YugiohROM.ACADEMY_LOCATIONS_THUMBS.start + 12 + period * 4, locations_palette_table)
    for location in range(26):
        write_u32(payload, locations_bitmap_table + location * 4, locations_bitmap_data + location * (4 + 6144))
        write_u32(payload, locations_palette_table + location * 4, locations_palette_data + location * 128)

    return payload


def save_paletted_image(path, size, colors, pixels):
    image = Image.fromarray(np.asarray(pixels, dtype=np.uint8), mode="P")
    palette = []
    for color in colors:
        palette.extend(color)
    palette.extend([0, 0, 0] * (256 - len(colors)))
    image.putpalette(palette)
    image.save(path)


class TestMemoryOperations(unittest.TestCase):
    def _make_temp_path(self, suffix):
        descriptor, path = tempfile.mkstemp(suffix=suffix)
        os.close(descriptor)
        return path

    def _write_temp_rom(self):
        payload = build_synthetic_rom()
        handle = tempfile.NamedTemporaryFile(suffix=".gba", delete=False)
        try:
            handle.write(payload)
            return handle.name
        finally:
            handle.close()

    def test_list_memory_paths_includes_card_tables(self):
        paths = {item.path for item in list_memory_paths()}
        self.assertIn("cards.high_res.bitmaps", paths)
        self.assertIn("sprites.characters.bitmaps", paths)
        self.assertIn("sprites.characters.palettes", paths)
        self.assertIn("sprites.locations.thumbs", paths)
        self.assertIn("strings.cards.names.en", paths)
        self.assertIn("strings.cards.texts.en.offsets", paths)

    def test_patch_string_entry(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".gba")
        try:
            patch_string_entry(source, "card_names_en", 1, "Z", output)
            patched = get_string_entry(output, "card_names_en", 1)
            self.assertEqual(patched, "Z")
        finally:
            os.unlink(source)
            os.unlink(output)

    def test_patch_card_image_writes_blocked_layout(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".gba")
        image_path = self._make_temp_path(".png")
        try:
            pixels = np.arange(80 * 80, dtype=np.uint8).reshape(80, 80)
            Image.fromarray(pixels, mode="L").save(image_path)

            patch_card_image(source, 0, image_path, output)
            memory = MemoryEmulator(output)
            card_region = memory[YugiohROM.CARD_HIGH_RES_BITMAPS.start, 80 * 80]
            patched = bytes(card_region.read_bytes(80 * 80))

            expected = split_blocks(pixels, (10, 10)).flatten().astype(np.uint8).tobytes()
            self.assertEqual(patched, expected)
        finally:
            os.unlink(source)
            os.unlink(output)
            os.unlink(image_path)

    def test_patch_duelist_sprite_writes_bitmap_and_palette(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".gba")
        image_path = self._make_temp_path(".png")
        try:
            pixels = (np.arange(64 * 64, dtype=np.uint8).reshape(64, 64) % 4)
            colors = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
            save_paletted_image(image_path, (64, 64), colors, pixels)

            patch_duelist_sprite(source, 0, 1, image_path, output)

            rom = YugiohROM(output)
            bitmap_region = rom.duelist_sprite_bitmap(0, 1)
            palette_region = rom.duelist_sprite_palette(0)
            expected_bitmap = split_blocks(pixels, DUELIST_SPRITE_BLOCKS).flatten().astype(np.uint8).tobytes()
            expected_palette = np.asarray(
                [rgb2gba(*color) for color in colors] + [0] * 60, dtype="<u2"
            ).tobytes()
            self.assertEqual(bytes(bitmap_region.read_bytes(4096)), expected_bitmap)
            self.assertEqual(bytes(palette_region.read_bytes(128)), expected_palette)
        finally:
            os.unlink(source)
            os.unlink(output)
            os.unlink(image_path)

    def test_patch_location_thumb_writes_bitmap_and_palette(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".gba")
        image_path = self._make_temp_path(".png")
        try:
            pixels = (np.arange(64 * 96, dtype=np.uint8).reshape(64, 96) % 4)
            colors = [(0, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
            save_paletted_image(image_path, (96, 64), colors, pixels)

            patch_location_thumb(source, "night", 2, image_path, output)

            rom = YugiohROM(output)
            bitmap_region = rom.location_thumb_bitmap(2, 2)
            palette_region = rom.location_thumb_palette(2, 2)
            expected_bitmap = split_blocks(pixels, LOCATION_THUMB_BLOCKS).flatten().astype(np.uint8).tobytes()
            expected_palette = np.asarray(
                [rgb2gba(*color) for color in colors] + [0] * 60, dtype="<u2"
            ).tobytes()
            self.assertEqual(bytes(bitmap_region.read_bytes(6144)), expected_bitmap)
            self.assertEqual(bytes(palette_region.read_bytes(128)), expected_palette)
        finally:
            os.unlink(source)
            os.unlink(output)
            os.unlink(image_path)

    def test_extract_card_artworks_writes_files(self):
        source = self._write_temp_rom()
        with tempfile.TemporaryDirectory() as output_dir:
            images = iter([Image.new("P", (80, 80), color=3), Image.new("P", (80, 80), color=7)])
            with patch.object(YugiohROM, "_read_card_artworks", return_value=images):
                extract_card_artworks(source, output_dir)

            self.assertTrue(os.path.exists(os.path.join(output_dir, "card-0000.png")))
            self.assertTrue(os.path.exists(os.path.join(output_dir, "card-0001.png")))
        os.unlink(source)

    def test_extract_duelist_sprites_writes_variation_files(self):
        source = self._write_temp_rom()
        with tempfile.TemporaryDirectory() as output_dir:
            sprite_sets = iter([
                [Image.new("P", (64, 64), color=1), Image.new("P", (64, 64), color=2)],
                [Image.new("P", (64, 64), color=3)],
            ])
            with (
                patch.object(YugiohROM, "_read_card_artworks", return_value=iter(())),
                patch.object(YugiohROM, "duelist_sprites", return_value=sprite_sets),
            ):
                extract_duelist_sprites(source, output_dir)

            self.assertTrue(
                os.path.exists(os.path.join(output_dir, "duelist-00-variation-0.png"))
            )
            self.assertTrue(
                os.path.exists(os.path.join(output_dir, "duelist-00-variation-1.png"))
            )
            self.assertTrue(
                os.path.exists(os.path.join(output_dir, "duelist-01-variation-0.png"))
            )
        os.unlink(source)

    def test_extract_location_thumbs_writes_period_files(self):
        source = self._write_temp_rom()
        with tempfile.TemporaryDirectory() as output_dir:
            thumbs = iter([
                [Image.new("P", (96, 64), color=1)],
                [Image.new("P", (96, 64), color=2)],
                [Image.new("P", (96, 64), color=3)],
            ])
            with (
                patch.object(YugiohROM, "_read_card_artworks", return_value=iter(())),
                patch.object(YugiohROM, "location_thumbs", return_value=thumbs),
            ):
                extract_location_thumbs(source, output_dir)

            self.assertTrue(os.path.exists(os.path.join(output_dir, "location-morning-00.png")))
            self.assertTrue(os.path.exists(os.path.join(output_dir, "location-afternoon-00.png")))
            self.assertTrue(os.path.exists(os.path.join(output_dir, "location-night-00.png")))
        os.unlink(source)

    def test_cli_build_parser_supports_sprite_commands(self):
        parser = build_parser()

        args = parser.parse_args(
            ["sprites", "extract-duelists", "--rom", "game.gba", "--output-dir", "out"]
        )

        self.assertEqual(args.command, "sprites")
        self.assertEqual(args.sprites_command, "extract-duelists")
        self.assertEqual(args.rom, "game.gba")
        self.assertEqual(args.output_dir, "out")
        self.assertTrue(callable(args.func))
        with patch("ygogxda.cli.extract_duelist_sprites") as extract_duelist_sprites_mock:
            result = args.func(args)

        extract_duelist_sprites_mock.assert_called_once_with("game.gba", "out")
        self.assertEqual(result, 0)

    def test_cli_build_parser_supports_sprite_patch_commands(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "sprites",
                "patch-location",
                "--rom",
                "game.gba",
                "--period",
                "night",
                "--location-index",
                "2",
                "--image",
                "thumb.png",
                "--output",
                "patched.gba",
            ]
        )

        self.assertEqual(args.command, "sprites")
        self.assertEqual(args.sprites_command, "patch-location")
        with patch("ygogxda.cli.patch_location_thumb") as patch_location_thumb_mock:
            result = args.func(args)

        patch_location_thumb_mock.assert_called_once_with(
            "game.gba", "night", 2, "thumb.png", "patched.gba"
        )
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
