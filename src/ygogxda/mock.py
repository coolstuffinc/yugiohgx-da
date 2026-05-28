import struct
from .registry import ASSETS
from .memory import BASE_ADDRESS
from .passwords import YugiohPasswords
from .japanese_encoding import encode as japanese_encode


def build_mock_gba(output_path: str = "mock.gba"):
    """
    Builds a synthetic GBA ROM file based on the ASSETS registry.
    This provides a valid file structure for testing without needing the original ROM.
    """
    # Determine ROM size based on registry
    max_addr = max(r.end for r in ASSETS.regions.values())
    payload = bytearray(max_addr - BASE_ADDRESS)

    def write_at(addr: int, data: bytes):
        offset = addr - BASE_ADDRESS
        if offset < 0 or offset + len(data) > len(payload):
            return
        payload[offset : offset + len(data)] = data

    # 1. GBA Header
    header = struct.pack(
        "<I156s12s4s2sBB B7sBBB2s",
        0xEA00002E,
        b"\x00" * 156,
        b"YUGIOHGXDA\x00\x00",
        b"BYGE",
        b"01",
        0x96,
        0x00,
        0x00,
        b"\x00" * 7,
        0x00,
        0x00,
        0,
        b"\x00\x00",
    )
    write_at(BASE_ADDRESS, header)

    # 2. Card Count
    total_reg = ASSETS.get_region("CARD_TOTAL_NUMBER")
    write_at(total_reg.start, struct.pack("<I", 3))

    # 3. String Tables
    for name, meta in ASSETS.string_tables.items():
        s_reg = ASSETS.get_region(meta.strings_region)
        o_reg = ASSETS.get_region(meta.offsets_region)

        entries = [f"Mock {name} {i}" for i in range(10)]
        if meta.encoding == "japanese_rom":
            entries = ["ア", "イ", "ウ"]
            encode = japanese_encode
        else:
            encode = lambda x: x.encode("utf-8")

        blob = b""
        offsets = []
        for e in entries:
            offsets.append(len(blob))
            blob += encode(e) + b"\x00"

        num_offsets = o_reg.size // 4
        full_offsets = offsets + [len(blob)] * (num_offsets - len(offsets))
        write_at(s_reg.start, blob)
        write_at(o_reg.start, struct.pack(f"<{len(full_offsets)}I", *full_offsets))

    # 4. Passwords
    pwd_reg = ASSETS.get_region("CARD_PASSWORD_KEYS")
    hashed = YugiohPasswords.forward_hash(bytes(int(c) for c in "12345678"))
    key = hashed ^ YugiohPasswords.padding(1)
    write_at(pwd_reg.start + 4, struct.pack("<I", key))

    # 5. Sprite Data
    # Use high ROM padding area for dummy sprite data
    dummy_base = 0x09800000
    next_dummy = dummy_base

    def alloc(size: int) -> int:
        nonlocal next_dummy
        addr = next_dummy
        next_dummy += size
        return addr

    for name, meta in ASSETS.sprites.items():
        b_reg = ASSETS.get_region(meta.bitmap_region)
        p_reg = ASSETS.get_region(meta.palette_region) if meta.palette_region else None

        if meta.is_pointer_table and meta.root_table_size > 0:
            half = meta.root_table_size // 2
            bmp_size = meta.entry_stride or (meta.width * meta.height * meta.bpp // 8)
            pal_size = meta.palette_stride or (meta.palette_colors * 2)
            bmp_tables = []
            for _ in range(half):
                loc_ptrs = [
                    alloc(meta.bitmap_header_skip + bmp_size) for _ in range(meta.count)
                ]
                table_addr = alloc(meta.count * 4)
                write_at(table_addr, struct.pack(f"<{meta.count}I", *loc_ptrs))
                bmp_tables.append(table_addr)
            pal_tables = []
            for _ in range(half):
                loc_ptrs = [alloc(pal_size) for _ in range(meta.count)]
                table_addr = alloc(meta.count * 4)
                write_at(table_addr, struct.pack(f"<{meta.count}I", *loc_ptrs))
                pal_tables.append(table_addr)
            header = struct.pack(f"<{half}I", *bmp_tables) + struct.pack(
                f"<{half}I", *pal_tables
            )
            write_at(b_reg.start, header)
            # Also handle palette data for the palette_region if it differs from bitmap region
            if p_reg and p_reg.start != b_reg.start:
                pal_data_total = b"".join(
                    b"\x00" * pal_size for _ in range(meta.count * half)
                )
                write_at(p_reg.start, pal_data_total)

        elif meta.is_pointer_table:
            bmp_size = meta.entry_stride or (meta.width * meta.height * meta.bpp // 8)
            if meta.pointers_are_packed:
                n = meta.count * meta.variations
                all_ptrs = [alloc(bmp_size) for _ in range(n)]
                write_at(b_reg.start, struct.pack(f"<{n}I", *all_ptrs))
            else:
                ptr_table = []
                for _ in range(meta.count):
                    if meta.variations > 1:
                        var_table_addr = alloc(meta.variations * 4)
                        ptr_table.append(var_table_addr)
                        var_ptrs = [alloc(bmp_size) for _v in range(meta.variations)]
                        write_at(
                            var_table_addr,
                            struct.pack(f"<{meta.variations}I", *var_ptrs),
                        )
                    else:
                        ptr_table.append(alloc(bmp_size))
                write_at(b_reg.start, struct.pack(f"<{meta.count}I", *ptr_table))

            # Write palette data
            if p_reg:
                pal_size = meta.palette_stride or 128
                if meta.palette_stride == 0:
                    # Palette is also pointer-based
                    pal_ptrs = [alloc(pal_size) for _ in range(meta.count)]
                    write_at(p_reg.start, struct.pack(f"<{meta.count}I", *pal_ptrs))
                else:
                    # Fixed stride palette
                    pal_data_total = b"".join(
                        b"\x00" * pal_size for _ in range(meta.count)
                    )
                    write_at(p_reg.start, pal_data_total)
        else:
            # Non-pointer sprite: write zero-filled bitmap and palette data
            bmp_size = meta.entry_stride or (meta.width * meta.height)
            pal_size = meta.palette_stride or (meta.palette_colors * 2)
            bmp_data_total = b"".join(b"\x00" * bmp_size for _ in range(meta.count))
            pal_data_total = b"".join(b"\x00" * pal_size for _ in range(meta.count))
            write_at(b_reg.start, bmp_data_total)
            if p_reg:
                write_at(p_reg.start, pal_data_total)

    with open(output_path, "wb") as f:
        f.write(payload)
    return payload
