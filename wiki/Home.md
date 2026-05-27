# Yu-Gi-Oh! GX Duel Academy — Reverse Engineering Wiki

## Card System
- **[Card Data Structure](Card-Data-Structure)** — Bit-packed stats table (ATK, DEF, level, type, attribute, spell/trap subtypes), lookup CLI
- **[Card Effect System](Card-Effect-System)** — Effect dispatch tables, state machines (duel screen, phases, battle, effect resolution), card-specific handler table
- **[Card Pile Format](Card-Pile-Format)** — 4bpp tiled background format for deck/card-selection UI

## Game Systems
- **[Exam Database](Exam-Database)** — Exam question structure, template strings with `$XXXX`/`%N`/`^NNN` placeholders
- **[Room Interaction System](Room-Interaction-System)** — PDA menu, room handlers, rank/title system, screen state machine
- **[Monster Record System](Monster-Record-System)** — Summon/Set/reposition record structure and animation state machine

## Reference
- **[GBA Technical Reference](GBA-Technical-Reference)** — Hardware specs, memory map, address translation, rendering pipeline
- **[Reverse Engineering Strategy](Reverse-Engineering-Strategy)** — Beginner's guide: string tracing, workflow loop, what to map first
- **[Ghidra Setup](Ghidra-Setup)** — Install, load ROM, MCP config, annotation workflow


---

### Quick Links
- [GitHub Repository](https://github.com/coolstuffinc/yugiohgx-da)
- [Issues / Bug Reports](https://github.com/coolstuffinc/yugiohgx-da/issues)
- [ROM: `ygogxda.gba`](https://github.com/coolstuffinc/yugiohgx-da) (32MB, not included)
- Toolchain: `uv run ygogxda <command>`
- Tests: `uv run python3 -m unittest discover -s tests -v`
- Ghidra MCP: `http://127.0.0.1:8080/`
