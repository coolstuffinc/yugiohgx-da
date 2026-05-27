# Reverse Engineering Strategy

A beginner's guide to mapping out Yu-Gi-Oh! GX Duel Academy using the `ygogxda` toolchain + Ghidra.

## Core Principle: Strings Are Anchors

Human-readable text is the most direct link between the binary and its behavior. Every menu label, dialog prompt, error message, and phase indicator is stored as a string that gets loaded by a function just before it's displayed. **Find the string → find the function.**

## The Workflow Loop

```
1. Pick a target string (e.g. "Schedule Duel")
2. Find its ROM address via ygogxda
3. Search for code references to that address (Ghidra xrefs)
4. Identify the function that loads it
5. Rename the function based on the string's purpose
6. Annotate in Ghidra via MCP
7. Repeat
```

## Where to Start

### 1. UI Strings (`ui_en` table)

Extract the English UI string table to find menu labels, dialog text, and prompts:

```sh
uv run ygogxda strings extract ui_en
```

Good first targets:
- **PDA menu**: `"PDA Menu"`, `"Schedule Duel"`, `"Check Deck"`, `"View Messages"` — leads to the main menu handler
- **Duel phases**: `"Draw Phase"`, `"Battle Phase"`, `"End Turn"` — reveals the duel state machine
- **Dialogs**: `"Do you accept this duel request?"`, `"You have a new message"` — finds the dialog system

### 2. Card Names (`card_names_en`)

Extract card names to map the card database:

```sh
uv run ygogxda strings extract card_names_en
```

Cross-reference card IDs with the stats table at `CARD_STATS` (`0x08F243CC`) to decode ATK, DEF, level, type.

### 3. Card Texts (`card_texts_en`)

The effect text for every card:

```sh
uv run ygogxda card lookup --rom ygogxda.gba --ordinal N --text
```

Useful for tracing card-specific effect handlers back to the `0x097DA800` dispatch table.

## Ghidra Integration

After finding a function via string tracing:

1. **Decompile** it in Ghidra or via MCP: `ghidra_decompile_function("FUN_0801234")`
2. **Name it** with a descriptive prefix:
   - `state_machine_*` — switch-case state machines
   - `effect_*` — effect system functions
   - `load_*` / `render_*` / `draw_*` — data loading or rendering
   - `show_*` — UI prompts and dialogs
3. **Add a comment** with what it does (not how)
4. **Check callers** — a function used by 3+ different contexts may be a general utility, not the specific handler you want

## What to Map First

| System | Entry Point | Why |
|--------|-------------|-----|
| **PDA menu** | `ui_en` strings about scheduling/management | Self-contained, high interaction, clear state machine |
| **Duel screen** | Phase strings ("Draw Phase", "Battle Phase") | Fixed layout, stable UI, phase flow is documented |
| **Card database** | Card names + stats table | Fully decoded (see [Card Data Structure](Card-Data-Structure)), CLI tooling ready |
| **Effect system** | Effect dispatch at `0x080502FC` | 3-layer dispatch, state machines documented (see [Card Effect System](Card-Effect-System)) |

## Common Pitfalls

- **One string, many callers**: A string like "Not enough cards" may be referenced from multiple places — you need the *caller* that represents the game logic, not the rendering utility
- **Functions with >3 distinct call sites**: Likely a utility (e.g. `ask_question`), not the handler you want. Look one level up in the call graph
- **Memory regions you haven't mapped**: If you find an unknown address, add it to `coverage.py` and `memory_map.py` before hardcoding it anywhere

## Tools Reference

```sh
uv run ygogxda strings extract <table>   # Dump a string table to CSV
uv run ygogxda card lookup --ordinal N   # Card lookup by index
uv run ygogxda card lookup --ordinal N --stats  # With decoded stats
uv run ygogxda card lookup --ordinal N --text   # With effect text
uv run ygogxda card patch                # Modify card stats
uv run ygogxda memory dump <region>      # Inspect raw memory region
uv run python3 -m unittest discover -s tests -v  # Run tests
```

See [Ghidra Setup](Ghidra-Setup) for MCP annotation setup.
