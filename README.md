# yugiohgx-da
Reverse Engineering the game Yu-Gi-Oh: Duel Academy (GBA)

## Checksums 
- This patcher was tested in the following versions of the game:

| hash name |  value                             | Filename                                          | Serial |
|-----------|------------------------------------|---------------------------------------------------|--------|
| md5sum    | `f62c47cbe08e1e3bcfcf9f1b84841a76` | Yu-Gi-Oh! GX - Duel Academy (U)(Independent).gba  | BYGE   |
| md5sum    | `e1cc21ebf4c3be179738ebbf44f25308` | Yu-Gi-Oh! GX - Duel Academy (Europe).gba          | BYGP   |

```diff
11,12c11,12
< 000000a0: 5955 4749 4f48 4758 4441 0000 4259 4750  YUGIOHGXDA..BYGP
< 000000b0: 4134 9600 0000 0000 0000 0000 00b1 0000  A4..............
---
> 000000a0: 5955 4749 4f48 4758 4441 0000 4259 4745  YUGIOHGXDA..BYGE
> 000000b0: 4134 9600 0000 0000 0000 0000 00bc 0000  A4..............
1016336,1016337c1016336,1016337
< 00f820f0: 0d00 0000 100a 0001 0000 0000 001c 1100  ................
< 00f82100: 180f 0c01 1d1d 1d10 040d 0707 1a1d 1d1a  ................
---
> 00f820f0: 0d00 0000 100a 0001 0000 0000 0017 0b01  ................
> 00f82100: 100e 0b01 1d1d 1d10 040d 0707 1a1d 1d1a  ................
1016340c1016340
< 00f82130: 101a 120e 1414 000a 121a 120e 0011 1a00  ................
---
> 00f82130: 101a 120e 1414 000a 121a 120e 1011 1a00  ................
1016348c1016348
< 00f821b0: 1e1f 1c1c 1e1c 1c1c 1c1e 1c1c 0c13 0000  ................
---
> 00f821b0: 1e1f 1c1c 1e1c 1c1c 1c1e 1c1c 0913 0000  ................
1568181c1568181
< 017edb40: 0000 0000 0000 0000 486d 3700 ad88 0a08  ........Hm7.....
---
> 017edb40: 0000 0000 0000 0000 b068 3700 ad88 0a08  .........h7.....
```

- The following versions DON'T work:

| hash name |  value                             | Filename                                                  |
|-----------|------------------------------------|-----------------------------------------------------------|
| md5sum    | `a44251198e1c9087c40262c34531a5a3` | Yu-Gi-Oh! Duel Monsters GX - Mezase Duel King (Japan).gba |

## Development with uv

Install dependencies with uv:

```bash
uv sync
```

Run the CLI:

```bash
uv run ygogxda memory paths
```

Extract card artworks:

```bash
uv run ygogxda sprites extract card --rom input.gba --output-dir cards
```

Patch a card artwork:

```bash
uv run ygogxda sprites patch card --rom input.gba --card-id 2 --image new.png --output patched.gba
```

Extract duelist sprites:

```bash
uv run ygogxda sprites extract duelist --rom input.gba --output-dir duelists
```

Patch a duelist sprite:

```bash
uv run ygogxda sprites patch duelist --rom input.gba --duelist-index 3 --variation-index 0 --image new.png --output patched.gba
```

Extract location thumbnails:

```bash
uv run ygogxda sprites extract location-thumb --rom input.gba --output-dir locations
```

Patch a location thumbnail:

```bash
uv run ygogxda sprites patch location-thumb --rom input.gba --period night --location-index 2 --image new.png --output patched.gba
```

Extract all string tables to CSV:

```bash
uv run ygogxda strings extract --rom input.gba
```

Extract one string table to a file:

```bash
uv run ygogxda strings extract --rom input.gba --table card_names_en --output card_names_en.csv
```

Extract UI strings:

```bash
uv run ygogxda strings extract --rom input.gba --table ui_en --output ui_en.csv
```

Patch a single string entry:

```bash
uv run ygogxda strings patch --rom input.gba --table card_names_en --index 2 --text "New Name" --output patched.gba
```

Bulk-patch string entries from an edited CSV (offsets are regenerated automatically):

```bash
uv run ygogxda strings patch --rom input.gba --table card_names_en --csv card_names_en.csv --output patched.gba
```
