class YugiohPasswords:
    def __init__(self, keys):
        self.keys = keys
        self.num_cards = len(keys)-1

    @staticmethod
    def forward_hash(raw_input: bytes):
        """ Perform a hash on the input """
        hashed = 0;
        i = 0;
        while 1:
            hashed = raw_input[i] + hashed * 16
            i += 1;
            if (not i < 8): break
        return hashed

    @staticmethod
    def padding(card_id: int):
        return (card_id * 0x343fd + 0x269ec3) >> 0x10 | 0x9ec30000;

    def expected_hash(self, card_id: int):
        """ Returns the expected hash for a given card id """
        key = self.keys[card_id & 0xffff]
        msg = self.padding(card_id & 0xffff)
        return key ^ msg

    def is_valid_password(self, password: str) -> bool:
        """ Checks if a password is a valid ygogxda password """
        return self.enter(password) != 0

    def enter(self, password: str) -> int:
        """
        Build a real-memory payload from a digit string
        NOTE: I know is overkill
        """
        payload = bytes([ord(digit)-ord('0') for digit in password])
        return self.enter_raw(payload)

    def enter_raw(self, raw_input: bytes) -> int:
        """
        Raw function transcripted from 0x080d5b88 (FUN_080d5b88)
        Returns a card index (ordinal) if the password is correct 0 otherwise.
        """
        hashed_input = self.forward_hash(raw_input)
        card_number = 1
        while 1:
            if (self.num_cards < card_number): return 0;
            expected_hash = self.expected_hash(card_number & 0xffff)
            if (hashed_input == expected_hash): break
            card_number += 1;
        return card_number & 0xffff

    @staticmethod
    def inverse_hash(hashed: int):
        """ Reversed eng. hash """
        i = 8;
        digits = ''
        while i > 0:
            i -= 1;
            digit = hashed // 16**i;
            hashed = hashed % 16**i
            digits += str(digit)
        return digits

    def unlock(self, card_id: int) -> str:
        """ Unlocks the password for a given card id """
        expected_hash = self.expected_hash(card_id)
        return self.inverse_hash(expected_hash)

