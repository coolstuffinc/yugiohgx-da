# Ghidra Setup

## Installation

1. Download Ghidra from [ghidra-sre.org](https://ghidra-sre.org/) (requires Java 17+)
2. Extract and run: `./ghidraRun` (Linux/macOS) or `ghidraRun.bat` (Windows)
3. Create a new project: **File → New Project → Non-Shared Project**

## Loading the ROM

1. **File → Import File** → select `ygogxda.gba`
2. Format: **Raw Binary** (GBA has no standard loader header for Ghidra)
3. Language: **ARM → little endian → ARMv4T** (GBA uses ARM7TDMI)
4. Base address: `0x08000000` (the GBA ROM mapping start)
5. After import, open the file in the CodeBrowser

> **Note**: If Ghidra asks about "Analysis", let it run the initial auto-analysis. It will identify most function boundaries automatically.

## Syncing to the Python Toolchain

The project maintains a local snapshot of all Ghidra function names (named + `FUN_*`) in `src/ygogxda/data/ghidra_functions.json`, exposed via the `ygogxda ghidra` CLI.

```sh
uv run ygogxda ghidra stats      # Show naming coverage stats
uv run ygogxda ghidra lookup 0x0805A754   # Look up function name by address
uv run ygogxda ghidra sync             # Pull latest from Ghidra HTTP server
uv run ygogxda ghidra sync --url http://localhost:8080  # Custom server URL
```

Run `sync` after any Ghidra rename session to keep the local JSON up to date.

## Ghidra MCP Server

This project uses [GhidraMCP](https://github.com/LAB02-Research/GhidraMCP) to annotate functions programmatically.

### Setup

1. Download the latest `GhidraMCP-x.x.zip` from the [releases page](https://github.com/LAB02-Research/GhidraMCP/releases)
2. Extract to `ghidra/GhidraMCP-release-x-x/` in the project root
3. In Ghidra: **File → Install Extensions** → add the `GhidraMCP-x.x.zip`
4. Restart Ghidra
5. **File → Configure → MCP Server** → enable, set port `8080`
6. In the project root, ensure `opencode.json` has the correct config:

```json
{
  "mcpServers": {
    "ghidra": {
      "url": "http://127.0.0.1:8080/"
    }
  }
}
```

### Usage

The project's agent uses Ghidra MCP to:

- **Rename functions**: `ghidra_rename_function("FUN_08007504", "state_machine_duel_screen")`
- **Rename data labels**: `ghidra_rename_data("0x08F243CC", "CARD_STATS_TABLE")`
- **Add comments**: `ghidra_set_decompiler_comment("0x08010904", "Load CARD_STATS_TABLE base pointer")`
- **Decompile**: `ghidra_decompile_function("FUN_08010814")`
- **Get cross-references**: `ghidra_get_xrefs_to("0x08F243CC")`

## Annotation Workflow

1. Load the ROM in Ghidra with auto-analysis
2. Use `ygogxda` CLI to extract strings and explore data
3. Find an interesting function via string tracing
4. Decompile it in Ghidra (or via MCP)
5. Determine its purpose
6. **Rename** it via MCP with a descriptive name
7. Add a **comment** explaining what it does
8. If a new data region is found, add a **data label** and update `coverage.py`

### Naming Conventions

| Prefix | Example | Purpose |
|--------|---------|---------|
| `state_machine_` | `state_machine_duel_screen` | Large switch-case state machines |
| `effect_` | `effect_dispatch_execute` | Card effect system functions |
| `card_effect_handler_` | `card_effect_handler_no_effect` | Card-specific effect handlers |
| `load_` | `load_card_text` | Data loading functions |
| `render_` / `draw_` | `draw_dialogue_text` | Rendering / drawing functions |
| `show_` | `show_confirmation_prompt` | UI prompt / dialogue functions |
| `build_` / `validate_` | `build_target_list_exec` | List construction / validation |

## Useful Ghidra Tips

- **Clean up the decompiler view**: Right-click → "Commit Params/Return" after identifying a function signature
- **Create structs**: Right-click in decompiler → "Auto Create Structure" for data layout analysis
- **Search for strings**: **Search → Program Text** or use the Defined Strings window
- **Follow xrefs**: Right-click a symbol → "References → Show References to"
- **Bookmark unknowns**: When you find something you don't understand, **Bookmark → Note** the address for later
