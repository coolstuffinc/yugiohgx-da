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

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from ygogxda.cli import build_parser
from ygogxda.memory import MemoryEmulator, mem_region
from ygogxda.passwords import YugiohPasswords
from ygogxda.registry import ASSETS
from ygogxda.memory_ops import (
    CARD_IMAGE_BLOCKS,
    DUELIST_SPRITE_BLOCKS,
    LOCATION_THUMB_BLOCKS,
    SUBDIR_CARDS,
    SUBDIR_DUELISTS,
    SUBDIR_LOCATIONS,
    SUBDIR_STRINGS,
    SUBDIR_MEMORY,
    canonical_output_path,
    dump_region,
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
from ygogxda.utils import split_blocks, join_blocks
from ygogxda.mock import build_mock_gba


LOCATION_POINTER_TABLE_HEADER_SIZE = 24
LOCATION_BITMAP_ENTRY_SIZE = 4 + 6144


def build_synthetic_rom():
    """Wrapper around the canonical mock builder for these tests."""
    return build_mock_gba("synthetic.gba")


class TestMemoryOperations(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_temp_rom(self):
        path = os.path.join(self.tmpdir.name, "game.gba")
        build_mock_gba(path)
        return path

    def test_list_memory_paths_includes_card_tables(self):
        from ygogxda.memory_map import list_memory_paths

        paths = {item.name for item in list_memory_paths()}
        self.assertIn("CARD_HIRES_BITMAPS", paths)
        self.assertIn("CARD_HIRES_PALETTES", paths)

    def test_patch_string_entry(self):
        source = self._write_temp_rom()
        output = os.path.join(self.tmpdir.name, "patched.gba")
        patch_string_entry(source, "card_names_en", 1, "Z", output)

        rom = YugiohROM(output)
        self.assertEqual(rom.card_names[1], "Z")

    def test_extract_card_artworks_writes_files(self):
        source = self._write_temp_rom()
        output_dir = Path(self.tmpdir.name) / "cards"
        extract_card_artworks(source, output_dir)
        self.assertTrue((output_dir / "card-0000.png").exists())

    def test_extract_duelist_sprites_writes_variation_files(self):
        source = self._write_temp_rom()
        output_dir = Path(self.tmpdir.name) / "duelists"
        extract_duelist_sprites(source, output_dir)
        self.assertTrue((output_dir / "duelist-00-variation-0.png").exists())

    def test_extract_location_thumbs_writes_period_files(self):
        source = self._write_temp_rom()
        output_dir = Path(self.tmpdir.name) / "locations"
        extract_location_thumbs(source, output_dir)
        self.assertTrue((output_dir / "location-morning-00.png").exists())

    def test_cli_build_parser_supports_sprite_commands(self):
        parser = build_parser()
        # Test extract duelist
        with patch("ygogxda.cli.extract_duelist_sprites") as mock:
            args = parser.parse_args(
                ["sprites", "extract", "--rom", "game.gba", "duelist"]
            )
            args.func(args)
            mock.assert_called_once_with("game.gba", None, jobs=None)

    def test_cli_build_parser_supports_card_patch_commands(self):
        parser = build_parser()
        with patch("ygogxda.cli.patch_sprite_resource") as mock:
            args = parser.parse_args(
                [
                    "sprites",
                    "patch",
                    "card",
                    "--rom",
                    "game.gba",
                    "--index",
                    "0",
                    "--image",
                    "art.png",
                    "--output",
                    "out.gba",
                ]
            )
            args.func(args)
            mock.assert_called_once()

    def test_extract_string_table_writes_csv(self):
        source = self._write_temp_rom()
        output = os.path.join(self.tmpdir.name, "strings.csv")
        extract_string_table(source, "card_names_en", output_file=output)
        self.assertTrue(os.path.exists(output))
        with open(output, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(rows[0]["text"], "Mock card_names_en 0")

    def test_extract_string_table_single_index(self):
        source = self._write_temp_rom()
        output = os.path.join(self.tmpdir.name, "single.csv")
        extract_string_table(source, "card_names_en", output_file=output, index=3)
        with open(output, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["index"], "3")

    def test_patch_string_table_bulk_roundtrip(self):
        source = self._write_temp_rom()
        csv_path = os.path.join(self.tmpdir.name, "patch.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "text"])
            writer.writerow([0, "New Name 0"])
            writer.writerow([2, "New Name 2"])

        output = os.path.join(self.tmpdir.name, "bulk.gba")
        patch_string_table_bulk(source, "card_names_en", csv_path, output)

        rom = YugiohROM(output)
        self.assertEqual(rom.card_names[0], "New Name 0")
        self.assertEqual(rom.card_names[1], "Mock card_names_en 1")  # Unchanged
        self.assertEqual(rom.card_names[2], "New Name 2")


class TestCanonicalOutputPath(unittest.TestCase):
    def test_appends_extracted_suffix(self):
        self.assertEqual(str(canonical_output_path("game.gba")), "game.gba.extracted")


class TestExtractUsesCanonicalPath(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_temp_rom(self, tmpdir):
        path = os.path.join(tmpdir, "game.gba")
        build_mock_gba(path)
        return path

    def test_extract_card_artworks_uses_canonical_path_when_no_output_dir(self):
        rom_path = self._write_temp_rom(self.tmpdir.name)
        with patch("PIL.Image.Image.save") as mock_save:
            extract_card_artworks(rom_path)
            # Should save to game.gba.extracted/sprites/cards/card-0000.png
            expected_path = (
                Path(rom_path).with_name("game.gba.extracted")
                / SUBDIR_CARDS
                / "card-0000.png"
            )
            mock_save.assert_any_call(expected_path)


class TestCLIExtractCanonicalPath(unittest.TestCase):
    def test_cli_sprites_extract_card_without_output_dir(self):
        parser = build_parser()
        with patch("ygogxda.cli.extract_card_artworks") as mock:
            args = parser.parse_args(
                ["sprites", "extract", "--rom", "game.gba", "card"]
            )
            args.func(args)
            mock.assert_called_once_with("game.gba", None, jobs=None)

    def test_cli_sprites_extract_duelist_without_output_dir(self):
        parser = build_parser()
        with patch("ygogxda.cli.extract_duelist_sprites") as mock:
            args = parser.parse_args(
                ["sprites", "extract", "--rom", "game.gba", "duelist"]
            )
            args.func(args)
            mock.assert_called_once_with("game.gba", None, jobs=None)


class TestDumpRegionCanonicalPath(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_temp_rom(self, tmpdir):
        path = os.path.join(tmpdir, "game.gba")
        build_mock_gba(path)
        return path

    def test_dump_region_uses_canonical_path_when_no_output_file(self):
        rom_path = self._write_temp_rom(self.tmpdir.name)
        dump_region(rom_path, "CARD_NAMES_EN")
        expected = (
            Path(rom_path).with_name("game.gba.extracted")
            / SUBDIR_MEMORY
            / "CARD_NAMES_EN.bin"
        )
        self.assertTrue(expected.exists())


class TestSpriteEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_temp_rom(self):
        path = os.path.join(self.tmpdir.name, "game.gba")
        build_mock_gba(path)
        return path

    def test_null_variation_pointer_non_packed(self):
        source = self._write_temp_rom()
        rom = YugiohROM(source)
        b_reg = ASSETS.get_region("CHAR_BITMAPS")
        ptrs = rom.rom[b_reg.slice].read_pointers(29)
        ptrs_list = [ptrs] if isinstance(ptrs, int) else ptrs
        var_table_addr = ptrs_list[0]
        rom.rom[mem_region(var_table_addr + 2 * 4, 4)] = b"\x00\x00\x00\x00"
        image = rom.get_sprite("duelist", 0, 2)
        self.assertEqual(image.size, (64, 64))
        pixels = np.asarray(image)
        self.assertTrue((pixels == 0).all())

    def test_null_variation_pointer_non_packed_second_var(self):
        source = self._write_temp_rom()
        rom = YugiohROM(source)
        b_reg = ASSETS.get_region("CHAR_BITMAPS")
        ptrs = rom.rom[b_reg.slice].read_pointers(29)
        ptrs_list = [ptrs] if isinstance(ptrs, int) else ptrs
        var_table_addr = ptrs_list[0]
        rom.rom[mem_region(var_table_addr + 1 * 4, 4)] = b"\x00\x00\x00\x00"
        image = rom.get_sprite("duelist", 0, 1)
        self.assertEqual(image.size, (64, 64))
        pixels = np.asarray(image)
        self.assertTrue((pixels == 0).all())

    def test_sprite_collection_encode_decode_roundtrip(self):
        source = self._write_temp_rom()
        rom = YugiohROM(source)
        col = rom.collections["card"]
        bmp, pal = col.getter(rom, 0)
        image = col.decode(bmp, pal)
        bmp2, pal2 = col.encode(image)
        self.assertEqual(bmp, bmp2)
        self.assertEqual(pal, pal2)

    def test_sprite_patch_roundtrip_via_rom(self):
        source = self._write_temp_rom()
        rom = YugiohROM(source)
        arr = np.zeros((64, 64), dtype=np.uint8)
        arr[16:48, 16:48] = 1
        img = Image.fromarray(arr, mode="P")
        rom.patch_sprite("duelist", 0, img, 0)
        output = os.path.join(self.tmpdir.name, "patched.gba")
        rom.save(output)
        rom2 = YugiohROM(output)
        result = rom2.get_sprite("duelist", 0, 0)
        result_arr = np.asarray(result)
        self.assertEqual(result_arr[0, 0], 0)
        self.assertEqual(result_arr[24, 24], 1)

    def test_location_thumb_non_packed_getter(self):
        source = self._write_temp_rom()
        rom = YugiohROM(source)
        col = rom.collections["location-thumb"]
        bmp, pal = col.getter(rom, 0, 0)
        self.assertEqual(len(bmp), 96 * 64)
        self.assertEqual(len(pal), 128)

    def test_card_pack_getter_returns_non_zero(self):
        source = self._write_temp_rom()
        rom = YugiohROM(source)
        col = rom.collections["card-pack"]
        bmp, pal = col.getter(rom, 0)
        self.assertEqual(len(bmp), 64 * 88)
        self.assertEqual(len(pal), 96)

    def test_hash_manifest_written_on_extract(self):
        import json

        source = self._write_temp_rom()
        from ygogxda.memory_ops import extract_card_packs

        output_dir = Path(self.tmpdir.name) / "packs"
        extract_card_packs(source, output_dir)
        manifest = output_dir / "hashes.json"
        self.assertTrue(manifest.exists())
        data = json.loads(manifest.read_text())
        self.assertIn("card_pack-00.png", data)
        self.assertEqual(len(data), 49)


if __name__ == "__main__":
    unittest.main()
