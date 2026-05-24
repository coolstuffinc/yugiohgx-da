import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ygogxda.japanese_encoding import decode, encode


# ROM bytes for ブルーアイズ・ホワイト・ドラゴン (Blue-Eyes White Dragon)
# Extracted from japanese_encondings.py (big-endian byte order).
_BLUE_EYES_BYTES = (
    0xF284F299F08BF1D0F1D2F1E8F084F289F29DF1D2F1F6F084F1F7F297F1E2F2A1
    .to_bytes(32, 'big')
)
_BLUE_EYES_TEXT = 'ブルーアイズ\u30fbホワイト\u30fbドラゴン'


class TestDecode(unittest.TestCase):
    def test_blue_eyes_white_dragon(self):
        self.assertEqual(decode(_BLUE_EYES_BYTES), _BLUE_EYES_TEXT)

    def test_f1_range_ア_to_パ(self):
        # ア U+30A2 → F1 D0,  パ U+30D1 → F1 FF
        self.assertEqual(decode(bytes([0xF1, 0xD0])), 'ア')
        self.assertEqual(decode(bytes([0xF1, 0xFF])), 'パ')

    def test_f2_range_ヒ_to_ヾ(self):
        # ヒ U+30D2 → F2 80,  ン U+30F3 → F2 A1,  ヾ U+30FE → F2 AC
        self.assertEqual(decode(bytes([0xF2, 0x80])), 'ヒ')
        self.assertEqual(decode(bytes([0xF2, 0xA1])), 'ン')
        self.assertEqual(decode(bytes([0xF2, 0xAC])), 'ヾ')

    def test_exception_middle_dot(self):
        self.assertEqual(decode(bytes([0xF0, 0x84])), '・')

    def test_exception_long_vowel_mark(self):
        self.assertEqual(decode(bytes([0xF0, 0x8B])), 'ー')

    def test_null_bytes_are_skipped(self):
        data = bytes([0x00, 0xF2, 0xA1, 0x00])
        self.assertEqual(decode(data), 'ン')

    def test_ascii_passthrough(self):
        self.assertEqual(decode(b'Hello'), 'Hello')

    def test_empty_input(self):
        self.assertEqual(decode(b''), '')

    def test_unknown_f0_sequence_is_skipped(self):
        # Unknown F0 code should be skipped without error
        result = decode(bytes([0xF0, 0x99, 0xF2, 0xA1]))
        self.assertEqual(result, 'ン')


class TestEncode(unittest.TestCase):
    def test_blue_eyes_white_dragon(self):
        self.assertEqual(encode(_BLUE_EYES_TEXT), _BLUE_EYES_BYTES)

    def test_f1_range_ア(self):
        self.assertEqual(encode('ア'), bytes([0xF1, 0xD0]))

    def test_f1_range_パ(self):
        self.assertEqual(encode('パ'), bytes([0xF1, 0xFF]))

    def test_f2_range_ヒ(self):
        self.assertEqual(encode('ヒ'), bytes([0xF2, 0x80]))

    def test_f2_range_ン(self):
        self.assertEqual(encode('ン'), bytes([0xF2, 0xA1]))

    def test_exception_middle_dot(self):
        self.assertEqual(encode('・'), bytes([0xF0, 0x84]))

    def test_exception_long_vowel_mark(self):
        self.assertEqual(encode('ー'), bytes([0xF0, 0x8B]))

    def test_ascii_passthrough(self):
        self.assertEqual(encode('Hi'), b'Hi')

    def test_empty_input(self):
        self.assertEqual(encode(''), b'')


class TestRoundtrip(unittest.TestCase):
    def _roundtrip(self, text):
        self.assertEqual(decode(encode(text)), text)

    def test_all_f1_katakana(self):
        # ア to パ  (U+30A2–U+30D1)
        for cp in range(0x30A2, 0x30D2):
            self._roundtrip(chr(cp))

    def test_all_f2_katakana(self):
        # ヒ to ヾ  (U+30D2–U+30FE), excluding the two exceptions
        exceptions = {'\u30FB', '\u30FC'}
        for cp in range(0x30D2, 0x30FF):
            char = chr(cp)
            if char not in exceptions:
                self._roundtrip(char)

    def test_exceptions_roundtrip(self):
        self._roundtrip('・')
        self._roundtrip('ー')

    def test_mixed_ascii_and_katakana(self):
        self._roundtrip('No.' + 'ドラゴン')


if __name__ == '__main__':
    unittest.main()
