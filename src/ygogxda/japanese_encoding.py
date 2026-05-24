# Custom ROM encoding for Japanese text in Yu-Gi-Oh GX Duel Academy (GBA).
#
# Each Japanese character is stored as a 2-byte sequence [prefix, code] where:
#
#   Katakana (U+30A2 – U+30D1) → prefix 0xF1, code 0xD0–0xFF
#     decode: unicode = 0x2FD2 + code
#     encode: rom = unicode + 0xC12E  (code byte already ≥ 0x80)
#
#   Katakana (U+30D2 – U+30FE) → prefix 0xF2, code 0x80–0xAC
#     decode: unicode = 0x3052 + code   (i.e. 0x30D2 + (code − 0x80))
#     encode: raw = unicode + 0xC12E → code byte < 0x80, add 0x80 to force it
#
# A small set of characters do not follow the formula and are mapped explicitly
# to slots in the 0xF0 prefix page.
#
# Unified encode formula:
#   rom = ord(char) + _KATAKANA_OFFSET
#   if (rom & 0xFF) < 0x80: rom += 0x80
#
# ASCII bytes (0x20–0x7E) pass through unchanged.
# Null bytes (0x00) are treated as string terminators and skipped on decode.

_KATAKANA_OFFSET = 0xC12E

# Characters whose ROM encoding does not follow the linear formula.
_EXCEPTIONS_ENCODE = {
    '\u30FB': bytes([0xF0, 0x84]),  # ・ (katakana middle dot)
    '\u30FC': bytes([0xF0, 0x8B]),  # ー (katakana long vowel mark)
}

# Reverse map: raw bytes → Unicode character
_EXCEPTIONS_DECODE = {v: k for k, v in _EXCEPTIONS_ENCODE.items()}


def encode(text: str) -> bytes:
    """Encode a Unicode string into the ROM's custom Japanese byte sequence."""
    result = bytearray()
    for char in text:
        if char in _EXCEPTIONS_ENCODE:
            result.extend(_EXCEPTIONS_ENCODE[char])
        elif '\u30A2' <= char <= '\u30FE':
            rom = ord(char) + _KATAKANA_OFFSET
            if (rom & 0xFF) < 0x80:
                rom += 0x80
            result.append((rom >> 8) & 0xFF)
            result.append(rom & 0xFF)
        elif ord(char) < 0x80:
            # ASCII: single-byte passthrough
            result.append(ord(char))
        else:
            # Other Unicode characters (e.g. kanji) whose ROM encoding is not
            # yet known are emitted as UTF-8 as a best-effort fallback.
            result.extend(char.encode('utf-8'))
    return bytes(result)


def decode(data: bytes) -> str:
    """Decode a ROM byte buffer into a Unicode string."""
    result = []
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == 0x00:
            i += 1
            continue
        if byte >= 0xF0 and i + 1 < len(data):
            pair = bytes([byte, data[i + 1]])
            if pair in _EXCEPTIONS_DECODE:
                result.append(_EXCEPTIONS_DECODE[pair])
                i += 2
                continue
            prefix = byte
            code = data[i + 1]
            if prefix == 0xF1 and code >= 0xD0:
                # Katakana ア (U+30A2) to パ (U+30D1)
                result.append(chr(0x2FD2 + code))
                i += 2
                continue
            if prefix == 0xF2 and code >= 0x80:
                # Katakana ヒ (U+30D2) to ヾ (U+30FE)
                result.append(chr(0x3052 + code))
                i += 2
                continue
            # Unknown prefix-page sequence; skip both bytes.
            i += 2
            continue
        # Single-byte passthrough: the ROM stores ASCII characters as-is.
        # Multi-byte UTF-8 sequences are not expected in ROM Japanese text;
        # each non-prefix byte is treated as a standalone ASCII character.
        result.append(chr(byte))
        i += 1
    return ''.join(result)
