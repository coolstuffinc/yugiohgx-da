import argparse
import sys

from .memory_map import CANONICAL_STRING_TABLES, list_memory_paths
from .memory_ops import (
    dump_region,
    extract_card_artworks,
    extract_duelist_sprites,
    extract_location_thumbs,
    extract_string_table,
    patch_card_image,
    patch_duelist_sprite,
    patch_location_thumb,
    patch_string_entry,
    patch_string_table_bulk,
    canonical_output_path,
    SUBDIR_CARDS,
    SUBDIR_DUELISTS,
    SUBDIR_LOCATIONS,
    LOCATION_PERIODS,
)


def _cmd_memory_paths(_args):
    for path in list_memory_paths():
        print(
            f"{path.path}\t0x{path.region.start:08x}\t0x{path.region.stop:08x}\t{path.size}\t{path.description}"
        )
    return 0


def _cmd_memory_dump(args):
    dump_region(args.rom, args.path, args.output)
    return 0


def _cmd_strings_extract(args):
    if args.index is not None and args.table is None:
        print("error: --index requires --table", file=sys.stderr)
        return 1
    if args.table is None:
        for name in sorted(CANONICAL_STRING_TABLES.keys()):
            extract_string_table(args.rom, name, output_file=f"{name}.csv")
    else:
        extract_string_table(args.rom, args.table, output_file=args.output, index=args.index)
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
    extract_card_artworks(args.rom, args.output_dir)
    return 0


def _cmd_sprites_extract_duelists(args):
    extract_duelist_sprites(args.rom, args.output_dir)
    return 0


def _cmd_sprites_extract_locations(args):
    extract_location_thumbs(args.rom, args.output_dir)
    return 0


def _cmd_sprites_patch_card(args):
    patch_card_image(args.rom, args.card_id, args.image, args.output)
    return 0


def _cmd_sprites_patch_duelist(args):
    patch_duelist_sprite(args.rom, args.duelist_index, args.variation_index, args.image, args.output)
    return 0


def _cmd_sprites_patch_location(args):
    patch_location_thumb(args.rom, args.period, args.location_index, args.image, args.output)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="ygogxda")
    subparsers = parser.add_subparsers(dest="command")

    # ── memory ────────────────────────────────────────────────────────────────
    memory_parser = subparsers.add_parser("memory", help="Memory mapping utilities")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")

    paths_parser = memory_subparsers.add_parser("paths", help="List canonical memory paths")
    paths_parser.set_defaults(func=_cmd_memory_paths)

    dump_parser = memory_subparsers.add_parser("dump", help="Dump bytes from a canonical memory path")
    dump_parser.add_argument("--rom", required=True, help="Input ROM file")
    dump_parser.add_argument("--path", required=True, help="Canonical memory path")
    dump_parser.add_argument("--output", required=True, help="Output dump file")
    dump_parser.set_defaults(func=_cmd_memory_dump)

    # ── strings ───────────────────────────────────────────────────────────────
    strings_parser = subparsers.add_parser("strings", help="String table extraction and patching")
    strings_subparsers = strings_parser.add_subparsers(dest="strings_action")

    strings_extract_parser = strings_subparsers.add_parser(
        "extract", help="Extract string table entries to CSV"
    )
    strings_extract_parser.add_argument("--rom", required=True, help="Input ROM file")
    strings_extract_parser.add_argument(
        "--table",
        choices=sorted(CANONICAL_STRING_TABLES.keys()),
        help="String table to extract (default: all tables)",
    )
    strings_extract_parser.add_argument(
        "--index", type=int, help="Extract a single entry by index (requires --table)"
    )
    strings_extract_parser.add_argument(
        "--output", help="Output CSV file (default: stdout when --table given)"
    )
    strings_extract_parser.set_defaults(func=_cmd_strings_extract)

    strings_patch_parser = strings_subparsers.add_parser(
        "patch", help="Patch string table entries"
    )
    strings_patch_parser.add_argument("--rom", required=True, help="Input ROM file")
    strings_patch_parser.add_argument(
        "--table",
        required=True,
        choices=sorted(CANONICAL_STRING_TABLES.keys()),
        help="String table to patch",
    )
    strings_patch_parser.add_argument("--output", required=True, help="Output ROM file")
    strings_patch_mode = strings_patch_parser.add_mutually_exclusive_group(required=True)
    strings_patch_mode.add_argument(
        "--csv", dest="csv_file", metavar="FILE", help="Bulk patch from CSV file"
    )
    strings_patch_mode.add_argument(
        "--text", help="New text value for a single entry (requires --index)"
    )
    strings_patch_parser.add_argument(
        "--index", type=int, help="Entry index (required with --text)"
    )
    strings_patch_parser.set_defaults(func=_cmd_strings_patch)

    # ── sprites ───────────────────────────────────────────────────────────────
    sprites_parser = subparsers.add_parser("sprites", help="Sprite extraction and patching")
    sprites_action_subparsers = sprites_parser.add_subparsers(dest="sprites_action")

    # sprites extract
    sprites_extract_parser = sprites_action_subparsers.add_parser("extract", help="Extract sprites")
    sprites_extract_subparsers = sprites_extract_parser.add_subparsers(dest="sprites_resource")

    sprites_extract_card_parser = sprites_extract_subparsers.add_parser(
        "card", help="Extract all high-resolution card artworks"
    )
    sprites_extract_card_parser.add_argument("--rom", required=True, help="Input ROM file")
    sprites_extract_card_parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for extracted images (default: <rom>.extracted/sprites/cards/)",
    )
    sprites_extract_card_parser.set_defaults(func=_cmd_sprites_extract_cards)

    sprites_extract_duelist_parser = sprites_extract_subparsers.add_parser(
        "duelist", help="Extract all duelist sprite variations"
    )
    sprites_extract_duelist_parser.add_argument("--rom", required=True, help="Input ROM file")
    sprites_extract_duelist_parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for extracted images (default: <rom>.extracted/sprites/duelists/)",
    )
    sprites_extract_duelist_parser.set_defaults(func=_cmd_sprites_extract_duelists)

    sprites_extract_location_parser = sprites_extract_subparsers.add_parser(
        "location-thumb", help="Extract academy location thumbnails"
    )
    sprites_extract_location_parser.add_argument("--rom", required=True, help="Input ROM file")
    sprites_extract_location_parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for extracted images (default: <rom>.extracted/sprites/locations/)",
    )
    sprites_extract_location_parser.set_defaults(func=_cmd_sprites_extract_locations)

    # sprites patch
    sprites_patch_parser = sprites_action_subparsers.add_parser("patch", help="Patch sprites")
    sprites_patch_subparsers = sprites_patch_parser.add_subparsers(dest="sprites_resource")

    sprites_patch_card_parser = sprites_patch_subparsers.add_parser(
        "card", help="Patch one high-resolution card artwork from an input image"
    )
    sprites_patch_card_parser.add_argument("--rom", required=True, help="Input ROM file")
    sprites_patch_card_parser.add_argument("--card-id", type=int, required=True, help="Card ID to patch")
    sprites_patch_card_parser.add_argument("--image", required=True, help="Input image file")
    sprites_patch_card_parser.add_argument("--output", required=True, help="Output ROM file")
    sprites_patch_card_parser.set_defaults(func=_cmd_sprites_patch_card)

    sprites_patch_duelist_parser = sprites_patch_subparsers.add_parser(
        "duelist", help="Patch one duelist sprite variation from an input image"
    )
    sprites_patch_duelist_parser.add_argument("--rom", required=True, help="Input ROM file")
    sprites_patch_duelist_parser.add_argument(
        "--duelist-index", required=True, type=int, help="Duelist sprite set index"
    )
    sprites_patch_duelist_parser.add_argument(
        "--variation-index", required=True, type=int, help="Sprite variation index"
    )
    sprites_patch_duelist_parser.add_argument("--image", required=True, help="Input image file")
    sprites_patch_duelist_parser.add_argument("--output", required=True, help="Output ROM file")
    sprites_patch_duelist_parser.set_defaults(func=_cmd_sprites_patch_duelist)

    sprites_patch_location_parser = sprites_patch_subparsers.add_parser(
        "location-thumb", help="Patch one academy location thumbnail from an input image"
    )
    sprites_patch_location_parser.add_argument("--rom", required=True, help="Input ROM file")
    sprites_patch_location_parser.add_argument(
        "--period", required=True, choices=LOCATION_PERIODS, help="Time of day variant"
    )
    sprites_patch_location_parser.add_argument(
        "--location-index", required=True, type=int, help="Academy location index"
    )
    sprites_patch_location_parser.add_argument("--image", required=True, help="Input image file")
    sprites_patch_location_parser.add_argument("--output", required=True, help="Output ROM file")
    sprites_patch_location_parser.set_defaults(func=_cmd_sprites_patch_location)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except (KeyError, ValueError, IndexError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
