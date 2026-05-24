import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ygogxda.memory import BASE_ADDRESS, MemoryEmulator, mem_region


class TestMemoryEmulator(unittest.TestCase):
    def test_virtual_and_real_address_access(self):
        payload = bytearray(range(64))
        memory = MemoryEmulator(payload, region=mem_region(BASE_ADDRESS, len(payload)))

        self.assertEqual(bytes(memory[0:4].read_bytes(4)), bytes([0, 1, 2, 3]))
        self.assertEqual(
            bytes(memory[BASE_ADDRESS + 4:BASE_ADDRESS + 8].read_bytes(4)),
            bytes([4, 5, 6, 7]),
        )

    def test_tuple_region_and_patch(self):
        payload = bytearray(range(16))
        memory = MemoryEmulator(payload, region=mem_region(BASE_ADDRESS, len(payload)))

        chunk = memory[BASE_ADDRESS + 8, 4]
        self.assertEqual(bytes(chunk.read_bytes(4)), bytes([8, 9, 10, 11]))

        memory[mem_region(BASE_ADDRESS + 2, 5)] = b'abcde'
        self.assertEqual(bytes(memory[0:7].read_bytes(7)), b'\x00\x01abcde')


if __name__ == '__main__':
    unittest.main()
