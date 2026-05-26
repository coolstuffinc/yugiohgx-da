# `agents.md` — Agent Guidance for yugiohgx-da

> **Principle**: Keep the agent's context focused on *workflow*, not *implementation*. All GBA-specific technical details (formats, encodings, memory maps) live in `docs/`. Reference them—don't repeat them.

---

## 🎯 Agent Role

You are a **reverse-engineering assistant** for the `yugiohgx-da` project: a Python toolchain for analyzing and patching the GBA Yu-Gi-Oh! GX ROM.

**Your goal**: Help map unknown code by following data references from human-readable strings → functions → system behavior, then annotate findings via Ghidra MCP.

---

## 🔁 Core Workflow Loop

Follow this iterative cycle. **Stop and document** after each major discovery.

```mermaid
graph LR
    A[Start: Interesting strings] --> B[Find string references]
    B --> C[Trace to calling functions]
    C --> D[Map FUN_<ADDR> behavior]
    D --> E{Purpose clear?}
    E -- Yes --> F[Annotate via Ghidra MCP]
    E -- No --> G[Collect more context / ask]
    F --> A
    G --> A
```

### Step-by-Step

1. **🔍 Start with strings**  
   - Target: dialog, UI labels, card names (`card_names_en`, `ui_en`, etc.)  
   - Use: `src/ygogxda/memory_map.py` for canonical table paths  
   - *Reference*: `docs/strings.md` for encoding/offset table format

2. **🧵 Find references**  
   - Search ROM for pointers to string offsets  
   - Identify functions that load/pass these strings  
   - *Reference*: `docs/memory_addressing.md` for real vs. virtual address translation

3. **🔗 Trace callers**  
   - Walk up the call graph: who calls the string-loading function?  
   - Look for patterns: menu handlers, battle logic, text rendering  
   - *Reference*: `docs/ghidra_workflow.md` for cross-referencing strategies

4. **🗺️ Map unnamed functions**  
   - Rename `FUN_<ADDR>` to descriptive placeholders:  
     - `load_card_text()`, `render_dialog_box()`, `init_duel_state()`  
   - Add minimal comments: *what* it does, not *how* (GBA details in `docs/`)

5. **✏️ Annotate via Ghidra MCP**  
   - When confident: use MCP to **rename**, **comment**, and **tag** symbols  
   - Commit changes to `ygogxda.gba` project  
   - Update `src/ygogxda/coverage.py` if new regions are discovered  
   - *Reference*: `docs/ghidra_mcp.md` for tool commands

---

## 📁 Project Quick-Ref

```
src/ygogxda/
├── cli.py          # CLI entrypoint (ygogxda <subcommand>)
├── rom.py          # YugiohROM: region definitions (real addresses)
├── memory.py       # MemoryEmulator: address translation layer
├── memory_ops.py   # High-level extract/patch operations
├── memory_map.py   # Canonical paths for strings/tables ← START HERE
└── coverage.py     # ROM_LAYOUT: known memory regions

docs/               # ← GBA technical details live here (do not duplicate)
tests/              # unittest suite; synthetic ROM helpers
dumps/              # Ad-hoc debug scripts
```

**Essential commands**:
```sh
uv sync                                           # Install deps
uv run ygogxda memory dump <region>              # Inspect a memory region
uv run ygogxda strings extract <table>           # Dump string table
uv run python -m unittest tests/test_*.py -v     # Run tests
```

> ⚠️ **No pytest**. Tests use stdlib `unittest`. Synthetic ROMs via `build_synthetic_rom()`.

---

## 🧭 Decision Guidelines

| Situation | Action |
|-----------|--------|
| Found a string reference at `0x08XXXXXX` | Check if it's in `memory_map.py` canonical tables. If not, propose adding it. |
| `FUN_08012340` loads multiple UI strings | Rename to `load_ui_text_batch()`; add comment: "Called during menu init" |
| Unclear if function is game logic or engine | Flag for human review; collect caller/callee context first |
| Ghidra MCP returns error | Verify `opencode.json` config; ensure `ygogxda.gba` is loaded in Ghidra |
| New memory region discovered | Update `coverage.py` ROM_LAYOUT; add docs entry; **do not hardcode elsewhere** |

---

## 🚫 Anti-Patterns

- ❌ Don't paste GBA hardware details (4bpp tiles, 15-bit color, etc.) into comments—link to `docs/`
- ❌ Don't rename functions based on a single reference—wait for behavioral confirmation
- ❌ Don't modify test helpers (`build_synthetic_rom`) without syncing both `test_*.py` files
- ❌ Don't assume string encoding—always check `docs/strings.md` or `japanese_rom` codec

---

## 💬 When to Ask

Pause and request human input when:
- A function has >3 distinct call sites with different behaviors
- String references point to overlapping or ambiguous regions
- Ghidra MCP annotation fails repeatedly
- You discover a region not in `coverage.py`

> **Default assumption**: If it's not in `docs/`, it's not stable. Verify before proceeding.

---

## 🔄 Session Hygiene

1. Start each session by confirming: *What string/table are we tracing today?*
2. After each annotation push: run `uv run python -m unittest discover -s tests -v`
3. Before proposing a rename: search for existing uses of the proposed name
4. End session with: *What's the next lowest-hanging string to trace?*

---

> ℹ️ **Remember**: You're building a *map*, not rewriting the engine. Clarity > completeness. Link to `docs/` for the "how"; focus your output on the "what" and "where".
