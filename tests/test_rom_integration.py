import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
import argparse
from pathlib import Path
from unittest.mock import patch

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from ygogxda.rom import YugiohROM
from ygogxda.mock import build_mock_gba
from ygogxda.memory_ops import (
    extract_card_artworks,
    extract_card_packs,
    extract_duelist_sprites,
    extract_location_thumbs,
    extract_card_pile_layers,
)

BASELINE_DIR = Path(__file__).parent / "baselines"
REAL_ROM = Path(__file__).parent.parent / "ygogxda.gba"


class TestYugiohRomIntegration(unittest.TestCase):
    def test_memory_map_injection_with_mocked_graphics(self):
        local_rom = os.getenv("YGOGXDA_TEST_ROM")

        if local_rom:
            rom = YugiohROM(local_rom)
        else:
            build_mock_gba("test_mock.gba")
            rom = YugiohROM("test_mock.gba")

        self.assertEqual(rom.game_title, "YUGIOHGXDA")
        self.assertIn(rom.game_code, ("BYGE", "BYGP"))

        if local_rom:
            self.assertEqual(len(rom.card_names), 1200)
            self.assertEqual(rom.num_cards, 1200)
        else:
            self.assertEqual(rom.num_cards, 3)
            # Match the values set in ygogxda/mock.py
            self.assertEqual(rom.card_names[0], "Mock card_names_en 0")
            self.assertEqual(rom.card_texts[0], "Mock card_texts_en 0")
            self.assertEqual(rom.card_names_jp[0], "ア")
            self.assertEqual(rom.passwords.enter("12345678"), 1)


class TestRealROMBaselines(unittest.TestCase):
    """Compare extracted sprites against known-good SHA256 baselines.
    Requires ygogxda.gba in the project root; skipped if absent.
    """

    @classmethod
    def setUpClass(cls):
        if not REAL_ROM.exists():
            raise unittest.SkipTest(f"{REAL_ROM} not available")

    def _compare(self, sprite_type, extract_fn, **extra_kw):
        baseline = BASELINE_DIR / f"{sprite_type}.json"
        self.assertTrue(baseline.exists(), f"No baseline file: {baseline}")
        expected = json.loads(baseline.read_text())

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            extract_fn(str(REAL_ROM), output_dir=out, **extra_kw)
            got = {
                png.name: hashlib.sha256(png.read_bytes()).hexdigest()
                for png in sorted(out.glob("*.png"))
            }

        self.assertEqual(got, expected)

    def test_cards(self):
        self._compare("cards", extract_card_artworks)

    def test_card_packs(self):
        self._compare("card_packs", extract_card_packs)

    def test_duelists(self):
        self._compare("duelists", extract_duelist_sprites)

    def test_locations(self):
        self._compare("locations", extract_location_thumbs)

    def test_card_piles(self):
        self._compare("card_piles", extract_card_pile_layers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--rom")
    args, remaining = parser.parse_known_args()
    if args.rom:
        os.environ["YGOGXDA_TEST_ROM"] = args.rom
    unittest.main(argv=[sys.argv[0], *remaining])
