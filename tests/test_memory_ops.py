import os
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from test_rom_integration import build_synthetic_rom
from ygogxda.memory import MemoryEmulator
from ygogxda.memory_map import list_memory_paths
from ygogxda.memory_ops import get_string_entry, patch_card_image, patch_string_entry
from ygogxda.rom import YugiohROM
from ygogxda.utils import split_blocks


class TestMemoryOperations(unittest.TestCase):
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
        self.assertIn("strings.cards.names.en", paths)
        self.assertIn("strings.cards.texts.en.offsets", paths)

    def test_patch_string_entry(self):
        source = self._write_temp_rom()
        output = tempfile.NamedTemporaryFile(suffix=".gba", delete=False).name
        try:
            patch_string_entry(source, "card_names_en", 1, "Z", output)
            patched = get_string_entry(output, "card_names_en", 1)
            self.assertEqual(patched, "Z")
        finally:
            os.unlink(source)
            os.unlink(output)

    def test_patch_card_image_writes_blocked_layout(self):
        source = self._write_temp_rom()
        output = tempfile.NamedTemporaryFile(suffix=".gba", delete=False).name
        image_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
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


if __name__ == "__main__":
    unittest.main()
