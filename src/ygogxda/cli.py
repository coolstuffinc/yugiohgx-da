import argparse
import sys
from pathlib import Path


class _HelpOnErrorParser(argparse.ArgumentParser):
    def error(self, message):
        msg = f"{self.prog}: error: {message}\n\n"
        sys.stderr.write(msg)
        self.print_help()
        sys.exit(2)


from .memory_map import CANONICAL_STRING_TABLES, list_memory_paths
from .registry import ASSETS as SPRITE_RESOURCES
from .ghidra_map import GhidraFunctionMap, lookup_address, _DEFAULT_GHIDRA_URL
from .memory_ops import (
    decode_card_stats,
    dump_region,
    extract_sprite_resource,
    patch_sprite_resource,
    extract_card_artworks,
    extract_duelist_sprites,
    extract_card_packs,
    extract_location_thumbs,
    extract_card_pile_layers,
    extract_string_table,
    lookup_card,
    patch_card_image,
    patch_card_pile_background_from_files,
    patch_card_stats,
    patch_string_entry,
    patch_string_table_bulk,
    canonical_output_path,
    SUBDIR_CARDS,
    SUBDIR_DUELISTS,
    SUBDIR_LOCATIONS,
    SUBDIR_STRINGS,
    SUBDIR_MEMORY,
    LOCATION_PERIODS,
)


def _cmd_memory_paths(_args):
    for r in list_memory_paths():
        print(f"{r.name}\t0x{r.start:08x}\t0x{r.end:08x}\t{r.size}\t{r.description}")
    return 0


def _cmd_memory_dump(args):
    dump_region(args.rom, args.path, args.output)
    return 0


def _cmd_memory_lookup(args):
    for addr_str in args.address:
        info = lookup_address(int(addr_str, 16))
        print(
            f"  {info['address']}  {info['function']:<45}  {info['region']:<20}  {info['category']:<10}  {info['description']}"
        )
    return 0


def _cmd_strings_extract(args):
    if args.index is not None and args.table is None:
        print("error: --index requires --table", file=sys.stderr)
        return 1
    if args.table is None:
        for name in sorted(CANONICAL_STRING_TABLES.keys()):
            extract_string_table(args.rom, name)
    else:
        extract_string_table(
            args.rom, args.table, output_file=args.output, index=args.index
        )
    return 0


def _cmd_strings_patch(args):
    if args.text is not None:
        if args.index is None:
            print("error: --index is required with --text", file=sys.stderr)
            return 1
        patch_string_entry(args.rom, args.table, args.index, args.text, args.output)
    else:
        patch_string_table_bulk(args.rom, args.table, args.csv_file, args.output)
    return 0


def _cmd_sprites_extract_cards(args):
    extract_card_artworks(args.rom, args.output_dir, jobs=getattr(args, "jobs", None))
    return 0


def _cmd_sprites_extract_duelists(args):
    extract_duelist_sprites(args.rom, args.output_dir, jobs=getattr(args, "jobs", None))
    return 0


def _cmd_sprites_extract_locations(args):
    extract_location_thumbs(args.rom, args.output_dir, jobs=getattr(args, "jobs", None))
    return 0


def _cmd_sprites_extract_card_pile(args):
    extract_card_pile_layers(args.rom, index=args.index, output_dir=args.output_dir)
    return 0


def _cmd_sprites_extract(args):
    rom_file = args.rom
    jobs = getattr(args, "jobs", None)
    if args.all:
        print("Extracting all sprites...")
        extract_card_artworks(rom_file, jobs=jobs)
        extract_card_packs(rom_file, jobs=jobs)
        extract_duelist_sprites(rom_file, jobs=jobs)
        extract_location_thumbs(rom_file, jobs=jobs)
        extract_card_pile_layers(rom_file)
        return 0

    resource_name = args.sprites_resource
    resource = SPRITE_RESOURCES.sprites[resource_name]
    if args.index is not None:
        vars_to_extract = (
            [args.variation]
            if args.variation is not None
            else range(resource.variations)
        )
        for v in vars_to_extract:
            out = extract_sprite_resource(
                rom_file, resource_name, args.index, variation=v
            )
            print(f"Extracted to {out}")
    else:
        print(f"Extracting all {resource_name} sprites...")
        # Map to specific commands for backward compatibility in CLI logic
        if resource_name == "card":
            _cmd_sprites_extract_cards(args)
        elif resource_name == "card-pack":
            extract_card_packs(rom_file, jobs=jobs)
        elif resource_name == "duelist":
            _cmd_sprites_extract_duelists(args)
        elif resource_name == "location-thumb":
            _cmd_sprites_extract_locations(args)
    return 0


def _cmd_sprites_patch(args):
    patch_sprite_resource(
        args.rom,
        args.sprites_resource,
        args.index,
        args.image,
        args.output,
        variation=args.variation or 0,
    )
    print(f"Patched {args.sprites_resource} index {args.index} in {args.output}")
    return 0


def _cmd_sprites_patch_card_pile(args):
    patch_card_pile_background_from_files(
        args.rom, index=args.index, layers_dir=args.layers_dir, output_rom=args.output
    )
    return 0


def _cmd_card_lookup(args):
    result = lookup_card(
        rom_file=args.rom,
        ordinal=args.ordinal,
        card_id=args.card_id,
        password=args.password,
        show_text=args.text,
        show_stats=args.stats,
    )
    print(f"ordinal:  {result['ordinal']}")
    print(f"card_id:  {result['card_id']}")
    print(f"name:     {result['name']}")
    print(f"password: {result['password']}")
    if result["text"] is not None:
        print(f"text:     {result['text']}")
    stats = result.get("stats")
    if stats is not None:
        print(f"category: {stats['category']}")
        if stats["category"] == "Monster":
            print(f"  type:      {stats['type']}")
            print(f"  attribute: {stats['attribute']}")
            print(f"  level:     {stats['level']}")
            print(f"  ATK:       {stats['atk']}")
            print(f"  DEF:       {stats['def']}")
            print(f"  subtype:   {stats['subtype']}")
        elif stats["category"] in ("Spell", "Trap"):
            print(f"  subtype: {stats['subtype']}")
    return 0


def _cmd_card_patch(args):
    kwargs = {
        k: v
        for k, v in vars(args).items()
        if k in ("category", "type", "attribute", "level", "atk", "defense")
        and v is not None
    }
    if "defense" in kwargs:
        kwargs["def"] = kwargs.pop("defense")
    new_val = patch_card_stats(args.rom, args.ordinal, args.output, **kwargs)
    decoded = decode_card_stats(new_val)
    print(f"Patched ordinal {args.ordinal}")
    print(f"  raw value: 0x{new_val:08X}")
    if decoded["category"] == "Monster":
        print(
            f"  type={decoded['type']}  attr={decoded['attribute']}  Lv{decoded['level']}  ATK={decoded['atk']}  DEF={decoded['def']}  ({decoded['subtype']})"
        )
    else:
        print(f"  {decoded['category']} ({decoded['subtype']})")
    return 0


def _cmd_ghidra_sync(args):
    fmap = GhidraFunctionMap()
    url = getattr(args, "url", None) or _DEFAULT_GHIDRA_URL
    try:
        total, delta = fmap.sync(ghidra_url=url)
    except Exception as exc:
        print(f"error: sync failed: {exc}", file=sys.stderr)
        return 1
    print(f"Synced {total} functions from Ghidra ({delta} new)")
    return 0


def _cmd_ghidra_stats(_args):
    fmap = GhidraFunctionMap()
    total, named, unnamed = fmap.stats()
    print(f"Total functions:  {total}")
    print(f"Named:           {named} ({named / total * 100:.1f}%)")
    print(f"Unnamed (FUN_):  {unnamed} ({unnamed / total * 100:.1f}%)")
    return 0


def _cmd_ghidra_lookup(args):
    for addr_str in args.address:
        info = lookup_address(int(addr_str, 16))
        print(
            f"  {info['address']}  {info['function']:<45}  {info['region']:<20}  {info['category']:<10}  {info['description']}"
        )
    return 0


def build_parser():
    parser = _HelpOnErrorParser(prog="ygogxda")
    subparsers = parser.add_subparsers(dest="command", parser_class=_HelpOnErrorParser)

    # memory
    memory_parser = subparsers.add_parser("memory", help="Memory mapping utilities")
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command", parser_class=_HelpOnErrorParser
    )
    memory_subparsers.add_parser(
        "paths", help="List canonical memory paths"
    ).set_defaults(func=_cmd_memory_paths)
    dump_parser = memory_subparsers.add_parser(
        "dump", help="Dump bytes from a canonical memory path"
    )
    dump_parser.add_argument("--rom", required=True)
    dump_parser.add_argument("--path", required=True)
    dump_parser.add_argument("--output", default=None)
    dump_parser.set_defaults(func=_cmd_memory_dump)
    lookup_parser = memory_subparsers.add_parser("lookup", help="Look up an address")
    lookup_parser.add_argument("address", nargs="+")
    lookup_parser.set_defaults(func=_cmd_memory_lookup)

    # strings
    strings_parser = subparsers.add_parser(
        "strings", help="String table extraction and patching"
    )
    strings_subparsers = strings_parser.add_subparsers(
        dest="strings_action", parser_class=_HelpOnErrorParser
    )
    extract_parser = strings_subparsers.add_parser(
        "extract", help="Extract string table"
    )
    extract_parser.add_argument("--rom", required=True)
    extract_parser.add_argument(
        "--table", choices=sorted(CANONICAL_STRING_TABLES.keys())
    )
    extract_parser.add_argument("--index", type=int)
    extract_parser.add_argument("--output")
    extract_parser.set_defaults(func=_cmd_strings_extract)
    patch_parser = strings_subparsers.add_parser("patch", help="Patch string table")
    patch_parser.add_argument("--rom", required=True)
    patch_parser.add_argument(
        "--table", required=True, choices=sorted(CANONICAL_STRING_TABLES.keys())
    )
    patch_parser.add_argument("--output", required=True)
    patch_group = patch_parser.add_mutually_exclusive_group(required=True)
    patch_group.add_argument("--csv", dest="csv_file")
    patch_group.add_argument("--text")
    patch_parser.add_argument("--index", type=int)
    patch_parser.set_defaults(func=_cmd_strings_patch)

    # sprites
    sprites_parser = subparsers.add_parser(
        "sprites", help="Sprite extraction and patching"
    )
    sprites_action_subparsers = sprites_parser.add_subparsers(
        dest="sprites_action", parser_class=_HelpOnErrorParser
    )

    extract_sprites_parser = sprites_action_subparsers.add_parser(
        "extract", help="Extract sprites"
    )
    extract_sprites_parser.add_argument("--rom", required=True)
    extract_sprites_parser.add_argument("--all", action="store_true")
    extract_sprites_parser.add_argument(
        "--jobs", type=int, default=None, help="Parallel workers (default: sequential)"
    )
    extract_sprites_sub = extract_sprites_parser.add_subparsers(
        dest="sprites_resource", parser_class=_HelpOnErrorParser
    )
    for name in SPRITE_RESOURCES.sprites:
        p = extract_sprites_sub.add_parser(name)
        p.add_argument("--index", type=int)
        p.add_argument("--variation", type=int)
        p.add_argument("--output-dir")
    extract_sprites_sub.add_parser("card-pile").set_defaults(
        func=_cmd_sprites_extract_card_pile
    )
    extract_sprites_parser.set_defaults(func=_cmd_sprites_extract)

    patch_sprites_parser = sprites_action_subparsers.add_parser(
        "patch", help="Patch sprites"
    )
    patch_sprites_sub = patch_sprites_parser.add_subparsers(
        dest="sprites_resource", parser_class=_HelpOnErrorParser
    )
    for name in SPRITE_RESOURCES.sprites:
        p = patch_sprites_sub.add_parser(name)
        p.add_argument("--rom", required=True)
        p.add_argument("--index", type=int)
        p.add_argument("--image", required=True)
        p.add_argument("--output", required=True)
        p.add_argument("--variation", type=int)
    pile_patch = patch_sprites_sub.add_parser("card-pile")
    pile_patch.add_argument("--rom", required=True)
    pile_patch.add_argument("--index", type=int)
    pile_patch.add_argument("--layers-dir")
    pile_patch.add_argument("--output", required=True)
    pile_patch.set_defaults(func=_cmd_sprites_patch_card_pile)
    patch_sprites_parser.set_defaults(func=_cmd_sprites_patch)

    # card
    card_parser = subparsers.add_parser("card", help="Card utilities")
    card_subparsers = card_parser.add_subparsers(
        dest="card_command", parser_class=_HelpOnErrorParser
    )
    lookup_p = card_subparsers.add_parser("lookup")
    lookup_p.add_argument("--rom", required=True)
    lookup_p.add_argument("--ordinal", type=int)
    lookup_p.add_argument("--card-id", type=int)
    lookup_p.add_argument("--password")
    lookup_p.add_argument("--text", action="store_true")
    lookup_p.add_argument("--stats", action="store_true")
    lookup_p.set_defaults(func=_cmd_card_lookup)
    patch_p = card_subparsers.add_parser("patch")
    patch_p.add_argument("--rom", required=True)
    patch_p.add_argument("--ordinal", type=int, required=True)
    patch_p.add_argument("--output", required=True)
    patch_p.add_argument("--category")
    patch_p.add_argument("--type")
    patch_p.add_argument("--attribute")
    patch_p.add_argument("--level", type=int)
    patch_p.add_argument("--atk", type=int)
    patch_p.add_argument("--def", dest="defense", type=int)
    patch_p.set_defaults(func=_cmd_card_patch)

    # ghidra
    ghidra_parser = subparsers.add_parser("ghidra", help="Ghidra tools")
    ghidra_subparsers = ghidra_parser.add_subparsers(
        dest="ghidra_command", parser_class=_HelpOnErrorParser
    )
    sync_p = ghidra_subparsers.add_parser("sync")
    sync_p.add_argument("--url")
    sync_p.set_defaults(func=_cmd_ghidra_sync)
    ghidra_subparsers.add_parser("stats").set_defaults(func=_cmd_ghidra_stats)
    lookup_g = ghidra_subparsers.add_parser("lookup")
    lookup_g.add_argument("address", nargs="+")
    lookup_g.set_defaults(func=_cmd_ghidra_lookup)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
