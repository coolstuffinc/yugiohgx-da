import os
import struct
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ygogxda.memory import MemoryEmulator
from ygogxda.passwords import YugiohPasswords
from ygogxda.memory_map import list_memory_paths
from ygogxda.memory_ops import get_string_entry, patch_card_image, patch_string_entry
from ygogxda.rom import YugiohROM
from ygogxda.utils import split_blocks


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
    return payload


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


if __name__ == "__main__":
    unittest.main()
