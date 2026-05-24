import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ygogxda.passwords import YugiohPasswords


class TestYugiohPasswords(unittest.TestCase):
    def test_forward_and_inverse_hash_roundtrip(self):
        raw_digits = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        hashed = YugiohPasswords.forward_hash(raw_digits)
        self.assertEqual(YugiohPasswords.inverse_hash(hashed), '12345678')

    def test_enter_and_unlock_without_rom(self):
        keys = [0] * 4
        password = '12345678'
        hashed = YugiohPasswords.forward_hash(bytes([int(ch) for ch in password]))
        keys[1] = hashed ^ YugiohPasswords.padding(1)

        passwords = YugiohPasswords(keys)

        self.assertEqual(passwords.enter(password), 1)
        self.assertTrue(passwords.is_valid_password(password))
        self.assertEqual(passwords.unlock(1), password)
        self.assertEqual(passwords.enter('00000000'), 0)


if __name__ == '__main__':
    unittest.main()
