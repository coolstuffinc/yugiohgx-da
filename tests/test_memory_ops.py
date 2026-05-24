import itertools
import csv
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ygogxda.cli import build_parser
from ygogxda.memory import MemoryEmulator
from ygogxda.passwords import YugiohPasswords
from ygogxda.memory_map import CANONICAL_STRING_TABLES, list_memory_paths
from ygogxda.memory_ops import (
    CARD_IMAGE_BLOCKS,
    DUELIST_SPRITE_BLOCKS,
    LOCATION_THUMB_BLOCKS,
    SUBDIR_CARDS,
    SUBDIR_DUELISTS,
    SUBDIR_LOCATIONS,
    canonical_output_path,
    extract_card_artworks,
    extract_duelist_sprites,
    extract_location_thumbs,
    extract_string_table,
    get_string_entry,
    patch_card_image,
    patch_duelist_sprite,
    patch_location_thumb,
    patch_string_entry,
    patch_string_table_bulk,
)
from ygogxda.rom import YugiohROM
from ygogxda.utils import split_blocks


LOCATION_POINTER_TABLE_HEADER_SIZE = 24
LOCATION_BITMAP_ENTRY_SIZE = 4 + 6144


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

    duelists_table_offset = YugiohROM.CHARACTERS_BITMAPS.start + 29 * 4
    duelists_bitmap_data_offset = duelists_table_offset + 5 * 4
    for index in range(29):
        write_u32(payload, YugiohROM.CHARACTERS_BITMAPS.start + index * 4, duelists_table_offset)
        write_u32(payload, YugiohROM.CHARACTERS_PALETTES.start + index * 4, YugiohROM.CHARACTERS_PALETTES.start + 29 * 4)
    for variation in range(5):
        write_u32(
            payload,
            duelists_table_offset + variation * 4,
            duelists_bitmap_data_offset + variation * 4096,
        )

    locations_bitmap_table = YugiohROM.ACADEMY_LOCATIONS_THUMBS.start + LOCATION_POINTER_TABLE_HEADER_SIZE
    locations_palette_table = locations_bitmap_table + 26 * 4
    locations_bitmap_data = locations_palette_table + 26 * 4
    locations_palette_data = locations_bitmap_data + 26 * LOCATION_BITMAP_ENTRY_SIZE
    for period in range(3):
        write_u32(payload, YugiohROM.ACADEMY_LOCATIONS_THUMBS.start + period * 4, locations_bitmap_table)
        write_u32(payload, YugiohROM.ACADEMY_LOCATIONS_THUMBS.start + 12 + period * 4, locations_palette_table)
    for location in range(26):
        write_u32(
            payload,
            locations_bitmap_table + location * 4,
            locations_bitmap_data + location * LOCATION_BITMAP_ENTRY_SIZE,
        )
        write_u32(payload, locations_palette_table + location * 4, locations_palette_data + location * 128)

    return payload


def save_paletted_image(path, colors, pixels):
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
        self.assertIn("strings.ui.en", paths)

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

    def test_patch_card_image_writes_bitmap_and_palette(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".gba")
        image_path = self._make_temp_path(".png")
        try:
            colors = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
            pixels = np.arange(80 * 80, dtype=np.uint8).reshape(80, 80) % len(colors)
            save_paletted_image(image_path, colors, pixels)

            patch_card_image(source, 0, image_path, output)
            rom = YugiohROM(output)
            bitmap_region = rom.card_artwork_bitmap(0)
            palette_region = rom.card_artwork_palette(0)
            patched = bytes(bitmap_region.read_bytes(80 * 80))

            expected = split_blocks(pixels, CARD_IMAGE_BLOCKS).flatten().astype(np.uint8).tobytes()
            self.assertEqual(patched, expected)
            self.assertNotEqual(bytes(palette_region.read_bytes(128)), b"\x00" * 128)
            artwork_image = next(iter(rom.card_images))
            with Image.open(image_path) as input_image:
                self.assertTrue(
                    np.array_equal(
                        np.asarray(artwork_image.convert("RGB")),
                        np.asarray(input_image.convert("RGB")),
                    )
                )
        finally:
            os.unlink(source)
            os.unlink(output)
            os.unlink(image_path)

    def test_patch_duelist_sprite_writes_bitmap_and_palette(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".gba")
        image_path = self._make_temp_path(".png")
        try:
            colors = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
            pixels = np.arange(64 * 64, dtype=np.uint8).reshape(64, 64) % len(colors)
            save_paletted_image(image_path, colors, pixels)

            patch_duelist_sprite(source, 0, 1, image_path, output)

            rom = YugiohROM(output)
            bitmap_region = rom.duelist_sprite_bitmap(0, 1)
            palette_region = rom.duelist_sprite_palette(0)
            expected_bitmap = split_blocks(pixels, DUELIST_SPRITE_BLOCKS).flatten().astype(np.uint8).tobytes()
            self.assertEqual(bytes(bitmap_region.read_bytes(4096)), expected_bitmap)
            self.assertNotEqual(bytes(palette_region.read_bytes(128)), b"\x00" * 128)
            sprite_image = next(iter(rom.duelist_sprites()))[1]
            with Image.open(image_path) as input_image:
                self.assertTrue(
                    np.array_equal(
                        np.asarray(sprite_image.convert("RGB")),
                        np.asarray(input_image.convert("RGB")),
                    )
                )
        finally:
            os.unlink(source)
            os.unlink(output)
            os.unlink(image_path)

    def test_patch_location_thumb_writes_bitmap_and_palette(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".gba")
        image_path = self._make_temp_path(".png")
        try:
            colors = [(0, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
            pixels = np.arange(64 * 96, dtype=np.uint8).reshape(64, 96) % len(colors)
            save_paletted_image(image_path, colors, pixels)

            patch_location_thumb(source, "night", 2, image_path, output)

            rom = YugiohROM(output)
            bitmap_region = rom.location_thumb_bitmap(2, 2)
            palette_region = rom.location_thumb_palette(2, 2)
            expected_bitmap = split_blocks(pixels, LOCATION_THUMB_BLOCKS).flatten().astype(np.uint8).tobytes()
            self.assertEqual(bytes(bitmap_region.read_bytes(6144)), expected_bitmap)
            self.assertNotEqual(bytes(palette_region.read_bytes(128)), b"\x00" * 128)
            thumb_image = next(itertools.islice(rom.location_thumbs(), 2, 3))[2]
            with Image.open(image_path) as input_image:
                self.assertTrue(
                    np.array_equal(
                        np.asarray(thumb_image.convert("RGB")),
                        np.asarray(input_image.convert("RGB")),
                    )
                )
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
            ["sprites", "extract", "duelist", "--rom", "game.gba", "--output-dir", "out"]
        )

        self.assertEqual(args.command, "sprites")
        self.assertEqual(args.sprites_action, "extract")
        self.assertEqual(args.sprites_resource, "duelist")
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
                "patch",
                "location-thumb",
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
        self.assertEqual(args.sprites_action, "patch")
        self.assertEqual(args.sprites_resource, "location-thumb")
        with patch("ygogxda.cli.patch_location_thumb") as patch_location_thumb_mock:
            result = args.func(args)

        patch_location_thumb_mock.assert_called_once_with(
            "game.gba", "night", 2, "thumb.png", "patched.gba"
        )
        self.assertEqual(result, 0)

    def test_cli_build_parser_supports_card_patch_commands(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "sprites",
                "patch",
                "card",
                "--rom",
                "game.gba",
                "--card-id",
                "2",
                "--image",
                "card.png",
                "--output",
                "patched.gba",
            ]
        )

        self.assertEqual(args.command, "sprites")
        self.assertEqual(args.sprites_action, "patch")
        self.assertEqual(args.sprites_resource, "card")
        with patch("ygogxda.cli.patch_card_image") as patch_card_image_mock:
            result = args.func(args)

        patch_card_image_mock.assert_called_once_with("game.gba", 2, "card.png", "patched.gba")
        self.assertEqual(result, 0)

    def test_extract_string_table_writes_csv(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".csv")
        try:
            extract_string_table(source, "card_names_en", output_file=output)
            with open(output, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 1200)
            self.assertEqual(rows[0]["index"], "0")
            self.assertEqual(rows[0]["text"], "A")
            self.assertEqual(rows[25]["text"], "Z")
        finally:
            os.unlink(source)
            os.unlink(output)

    def test_extract_string_table_single_index(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".csv")
        try:
            extract_string_table(source, "card_names_en", output_file=output, index=3)
            with open(output, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["index"], "3")
            self.assertEqual(rows[0]["text"], "D")
        finally:
            os.unlink(source)
            os.unlink(output)

    def test_extract_string_table_handles_invalid_utf8(self):
        source = self._write_temp_rom()
        output = self._make_temp_path(".csv")
        try:
            with open(source, "r+b") as rom_file:
                rom_file.seek(YugiohROM.CARD_NAMES_EN.start - 0x08000000)
                rom_file.write(b"\xff\x00")

            extract_string_table(source, "card_names_en", output_file=output, index=0)
            with open(output, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            replacement_char = "\ufffd"
            self.assertEqual(rows[0]["text"], replacement_char)
        finally:
            os.unlink(source)
            os.unlink(output)

    def test_patch_string_table_bulk_roundtrip(self):
        source = self._write_temp_rom()
        csv_path = self._make_temp_path(".csv")
        output = self._make_temp_path(".gba")
        try:
            # Replace entries 0 and 1 with same-length values
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["index", "text"])
                writer.writerow([0, "Z"])
                writer.writerow([1, "Y"])

            patch_string_table_bulk(source, "card_names_en", csv_path, output)

            self.assertEqual(get_string_entry(output, "card_names_en", 0), "Z")
            self.assertEqual(get_string_entry(output, "card_names_en", 1), "Y")
            self.assertEqual(get_string_entry(output, "card_names_en", 2), "C")
        finally:
            os.unlink(source)
            os.unlink(csv_path)
            os.unlink(output)

    def test_patch_string_table_bulk_preserves_raw_bytes_for_untouched_entries(self):
        source = self._write_temp_rom()
        csv_path = self._make_temp_path(".csv")
        output = self._make_temp_path(".gba")
        try:
            with open(source, "r+b") as rom_file:
                rom_file.seek(YugiohROM.CARD_NAMES_EN.start - 0x08000000 + 2)
                rom_file.write(b"\xff\x00")

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["index", "text"])
                writer.writerow([0, "Z"])

            patch_string_table_bulk(source, "card_names_en", csv_path, output)

            patched_memory = MemoryEmulator(output)
            start = YugiohROM.CARD_NAMES_EN.start + 2
            self.assertEqual(
                patched_memory[start, 2].read_bytes(2),
                b"\xff\x00",
            )
        finally:
            os.unlink(source)
            os.unlink(csv_path)
            os.unlink(output)

    def test_patch_string_table_bulk_overflow_raises(self):
        source = self._write_temp_rom()
        csv_path = self._make_temp_path(".csv")
        output = self._make_temp_path(".gba")
        try:
            # Writing a 20-char string to every entry produces 1200 * 21 = 25200 bytes,
            # which exceeds the 20475-byte CARD_NAMES_EN region.
            long_text = "A" * 20
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["index", "text"])
                for i in range(1200):
                    writer.writerow([i, long_text])

            with self.assertRaises(ValueError):
                patch_string_table_bulk(source, "card_names_en", csv_path, output)
        finally:
            os.unlink(source)
            os.unlink(csv_path)
            if os.path.exists(output):
                os.unlink(output)

    def test_cli_strings_extract(self):
        parser = build_parser()

        args = parser.parse_args(
            ["strings", "extract", "--rom", "game.gba", "--table", "card_names_en", "--output", "names.csv"]
        )

        self.assertEqual(args.command, "strings")
        self.assertEqual(args.strings_action, "extract")
        self.assertEqual(args.table, "card_names_en")
        self.assertEqual(args.output, "names.csv")
        self.assertTrue(callable(args.func))

    def test_cli_strings_extract_includes_ui_table_choice(self):
        parser = build_parser()
        args = parser.parse_args(
            ["strings", "extract", "--rom", "game.gba", "--table", "ui_en"]
        )
        self.assertIn("ui_en", CANONICAL_STRING_TABLES)
        self.assertEqual(args.table, "ui_en")

    def test_cli_strings_patch_single(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "strings", "patch",
                "--rom", "game.gba",
                "--table", "card_names_en",
                "--index", "5",
                "--text", "NewName",
                "--output", "patched.gba",
            ]
        )

        self.assertEqual(args.command, "strings")
        self.assertEqual(args.strings_action, "patch")
        self.assertEqual(args.table, "card_names_en")
        self.assertEqual(args.index, 5)
        self.assertEqual(args.text, "NewName")
        self.assertTrue(callable(args.func))
        with patch("ygogxda.cli.patch_string_entry") as mock_patch:
            result = args.func(args)

        mock_patch.assert_called_once_with("game.gba", "card_names_en", 5, "NewName", "patched.gba")
        self.assertEqual(result, 0)

    def test_cli_strings_patch_csv(self):
        parser = build_parser()

        args = parser.parse_args(
            [
                "strings", "patch",
                "--rom", "game.gba",
                "--table", "card_names_en",
                "--csv", "names.csv",
                "--output", "patched.gba",
            ]
        )

        self.assertEqual(args.command, "strings")
        self.assertEqual(args.strings_action, "patch")
        self.assertEqual(args.csv_file, "names.csv")
        self.assertTrue(callable(args.func))
        with patch("ygogxda.cli.patch_string_table_bulk") as mock_bulk:
            result = args.func(args)

        mock_bulk.assert_called_once_with("game.gba", "card_names_en", "names.csv", "patched.gba")
        self.assertEqual(result, 0)


class TestCanonicalOutputPath(unittest.TestCase):
    def test_appends_extracted_suffix(self):
        result = canonical_output_path("ygogxda.gba")
        self.assertEqual(result.name, "ygogxda.gba.extracted")

    def test_preserves_parent_directory(self):
        result = canonical_output_path("/some/path/game.gba")
        self.assertEqual(result.parent, Path("/some/path"))
        self.assertEqual(result.name, "game.gba.extracted")

    def test_subdir_constants_are_under_sprites(self):
        self.assertEqual(str(SUBDIR_CARDS), str(Path("sprites") / "cards"))
        self.assertEqual(str(SUBDIR_DUELISTS), str(Path("sprites") / "duelists"))
        self.assertEqual(str(SUBDIR_LOCATIONS), str(Path("sprites") / "locations"))


class TestExtractUsesCanonicalPath(unittest.TestCase):
    def _write_temp_rom(self, directory):
        payload = build_synthetic_rom()
        path = os.path.join(directory, "game.gba")
        with open(path, "wb") as f:
            f.write(payload)
        return path

    def test_extract_card_artworks_uses_canonical_path_when_no_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rom_path = self._write_temp_rom(tmpdir)
            images = iter([Image.new("P", (80, 80), color=3), Image.new("P", (80, 80), color=7)])
            with patch.object(YugiohROM, "_read_card_artworks", return_value=images):
                extract_card_artworks(rom_path)
            expected_dir = os.path.join(tmpdir, "game.gba.extracted", "sprites", "cards")
            self.assertTrue(os.path.exists(os.path.join(expected_dir, "card-0000.png")))
            self.assertTrue(os.path.exists(os.path.join(expected_dir, "card-0001.png")))

    def test_extract_duelist_sprites_uses_canonical_path_when_no_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rom_path = self._write_temp_rom(tmpdir)
            sprite_sets = iter([
                [Image.new("P", (64, 64), color=1), Image.new("P", (64, 64), color=2)],
            ])
            with (
                patch.object(YugiohROM, "_read_card_artworks", return_value=iter(())),
                patch.object(YugiohROM, "duelist_sprites", return_value=sprite_sets),
            ):
                extract_duelist_sprites(rom_path)
            expected_dir = os.path.join(tmpdir, "game.gba.extracted", "sprites", "duelists")
            self.assertTrue(os.path.exists(os.path.join(expected_dir, "duelist-00-variation-0.png")))
            self.assertTrue(os.path.exists(os.path.join(expected_dir, "duelist-00-variation-1.png")))

    def test_extract_location_thumbs_uses_canonical_path_when_no_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rom_path = self._write_temp_rom(tmpdir)
            thumbs = iter([
                [Image.new("P", (96, 64), color=1)],
                [Image.new("P", (96, 64), color=2)],
                [Image.new("P", (96, 64), color=3)],
            ])
            with (
                patch.object(YugiohROM, "_read_card_artworks", return_value=iter(())),
                patch.object(YugiohROM, "location_thumbs", return_value=thumbs),
            ):
                extract_location_thumbs(rom_path)
            expected_dir = os.path.join(tmpdir, "game.gba.extracted", "sprites", "locations")
            self.assertTrue(os.path.exists(os.path.join(expected_dir, "location-morning-00.png")))
            self.assertTrue(os.path.exists(os.path.join(expected_dir, "location-afternoon-00.png")))
            self.assertTrue(os.path.exists(os.path.join(expected_dir, "location-night-00.png")))


class TestCLIExtractCanonicalPath(unittest.TestCase):
    def test_cli_sprites_extract_card_without_output_dir(self):
        parser = build_parser()
        args = parser.parse_args(["sprites", "extract", "card", "--rom", "game.gba"])
        self.assertIsNone(args.output_dir)
        with patch("ygogxda.cli.extract_card_artworks") as mock:
            result = args.func(args)
        mock.assert_called_once_with("game.gba", None)
        self.assertEqual(result, 0)

    def test_cli_sprites_extract_duelist_without_output_dir(self):
        parser = build_parser()
        args = parser.parse_args(["sprites", "extract", "duelist", "--rom", "game.gba"])
        self.assertIsNone(args.output_dir)
        with patch("ygogxda.cli.extract_duelist_sprites") as mock:
            result = args.func(args)
        mock.assert_called_once_with("game.gba", None)
        self.assertEqual(result, 0)

    def test_cli_sprites_extract_location_without_output_dir(self):
        parser = build_parser()
        args = parser.parse_args(["sprites", "extract", "location-thumb", "--rom", "game.gba"])
        self.assertIsNone(args.output_dir)
        with patch("ygogxda.cli.extract_location_thumbs") as mock:
            result = args.func(args)
        mock.assert_called_once_with("game.gba", None)
        self.assertEqual(result, 0)

    def test_cli_sprites_extract_card_with_explicit_output_dir(self):
        parser = build_parser()
        args = parser.parse_args(
            ["sprites", "extract", "card", "--rom", "game.gba", "--output-dir", "mydir"]
        )
        self.assertEqual(args.output_dir, "mydir")
        with patch("ygogxda.cli.extract_card_artworks") as mock:
            result = args.func(args)
        mock.assert_called_once_with("game.gba", "mydir")
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
