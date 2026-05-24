import os
import struct
import sys
import unittest
import argparse
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ygogxda.memory import BASE_ADDRESS
from ygogxda.passwords import YugiohPasswords
from ygogxda.rom import YugiohROM


def write_bytes(payload, real_address, data):
    start = real_address - BASE_ADDRESS
    payload[start:start + len(data)] = data


def write_u16(payload, real_address, value):
    write_bytes(payload, real_address, struct.pack('<H', value))


def write_u32(payload, real_address, value):
    write_bytes(payload, real_address, struct.pack('<I', value))


def build_synthetic_rom():
    required_stops = [
        YugiohROM.CARD_HIGH_RES_BITMAPS.stop,
        YugiohROM.CARD_HIGH_RES_PALETTES.stop,
        YugiohROM.CARD_NAMES_OFFSETS_EN.stop,
        YugiohROM.CARD_TEXTS_OFFSETS_EN.stop,
        YugiohROM.CARD_PASSWORD_KEYS.stop,
        YugiohROM.CARD_NUMBER_TO_ID.stop,
        YugiohROM.CARD_NAMES_OFFSETS_JP.stop,
        YugiohROM.CARD_NAMES_JP.stop,
    ]
    payload = bytearray(max(required_stops) - BASE_ADDRESS)

    header = struct.pack(
        '<I156s12s4s2s1b1b1b7s1b1b2s',
        0xEA00002E,
        b'\x00' * 156,
        b'YUGIOHGXDA\x00\x00',
        b'BYGE',
        b'01',
        0,
        0,
        0,
        b'\x00' * 7,
        0,
        0,
        b'\x00\x00',
    )
    write_bytes(payload, BASE_ADDRESS, header)

    write_u32(payload, YugiohROM.CARD_TOTAL_NUMBER.start, 3)

    for i in range(1201):
        write_u32(payload, YugiohROM.CARD_NAMES_OFFSETS_EN.start + i * 4, i * 2)
        write_u32(payload, YugiohROM.CARD_TEXTS_OFFSETS_EN.start + i * 4, i * 3)
        write_u16(payload, YugiohROM.CARD_NUMBER_TO_ID.start + i * 2, i)
        write_u32(payload, YugiohROM.CARD_NAMES_OFFSETS_JP.start + i * 4, i * 3)

    names_data = bytearray()
    texts_data = bytearray()
    jp_names_data = bytearray()
    for i in range(1200):
        names_data.extend(bytes([ord('A') + (i % 26), 0]))
        texts_data.extend(bytes([ord('a') + (i % 26), ord('!'), 0]))
        # Two-byte katakana codeword (ア = F1 D0) followed by a null terminator
        jp_names_data.extend(bytes([0xF1, 0xD0, 0x00]))
    write_bytes(payload, YugiohROM.CARD_NAMES_EN.start, names_data)
    write_bytes(payload, YugiohROM.CARD_TEXTS_EN.start, texts_data)
    write_bytes(payload, YugiohROM.CARD_NAMES_JP.start, jp_names_data)

    password = '12345678'
    hashed = YugiohPasswords.forward_hash(bytes(int(ch) for ch in password))
    card_id = 1
    key = hashed ^ YugiohPasswords.padding(card_id)
    write_u32(payload, YugiohROM.CARD_PASSWORD_KEYS.start + card_id * 4, key)

    return payload


class TestYugiohRomIntegration(unittest.TestCase):
    def test_memory_map_injection_with_mocked_graphics(self):
        local_rom = os.getenv("YGOGXDA_TEST_ROM")

        with patch.object(YugiohROM, '_read_card_artworks', return_value=iter(())):
            if local_rom:
                rom = YugiohROM(local_rom)
            else:
                payload = build_synthetic_rom()
                rom = YugiohROM('ignored-by-memory-map', memory_map=payload)

        self.assertEqual(rom.game_title, 'YUGIOHGXDA')
        self.assertIn(rom.game_code, ('BYGE', 'BYGP'))
        self.assertEqual(len(rom.card_names), 1200)
        self.assertEqual(len(rom.card_texts), 1200)
        self.assertEqual(len(rom.card_names_jp), 1200)

        if local_rom:
            self.assertEqual(rom.num_cards, 1200)
        else:
            self.assertEqual(rom.num_cards, 3)
            self.assertEqual(rom.card_names[0], 'A')
            self.assertEqual(rom.card_texts[0], 'a!')
            self.assertEqual(rom.card_names_jp[0], 'ア')
            self.assertEqual(rom.passwords.enter('12345678'), 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--rom")
    args, remaining = parser.parse_known_args()
    if args.rom:
        os.environ["YGOGXDA_TEST_ROM"] = args.rom
    unittest.main(argv=[sys.argv[0], *remaining])
