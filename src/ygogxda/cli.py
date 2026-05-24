import argparse
import sys

from .memory_map import CANONICAL_STRING_TABLES, list_memory_paths
from .memory_ops import (
    dump_region,
    extract_card_artworks,
    extract_duelist_sprites,
    extract_location_thumbs,
    patch_card_image,
    patch_duelist_sprite,
    patch_location_thumb,
    patch_string_entry,
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


def _cmd_memory_patch_card_image(args):
    patch_card_image(args.rom, args.card_id, args.image, args.output)
    return 0


def _cmd_memory_patch_string(args):
    patch_string_entry(args.rom, args.table, args.index, args.text, args.output)
    return 0


def _cmd_sprites_extract_cards(args):
    extract_card_artworks(args.rom, args.output_dir)
    return 0


def _cmd_sprites_patch_card(args):
    patch_card_image(args.rom, args.card_id, args.image, args.output)
    return 0


def _cmd_sprites_extract_duelists(args):
    extract_duelist_sprites(args.rom, args.output_dir)
    return 0


def _cmd_sprites_extract_locations(args):
    extract_location_thumbs(args.rom, args.output_dir)
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

    memory_parser = subparsers.add_parser("memory", help="Memory mapping and patching utilities")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")

    paths_parser = memory_subparsers.add_parser("paths", help="List canonical memory paths")
    paths_parser.set_defaults(func=_cmd_memory_paths)

    dump_parser = memory_subparsers.add_parser("dump", help="Dump bytes from a canonical memory path")
    dump_parser.add_argument("--rom", required=True, help="Input ROM file")
    dump_parser.add_argument("--path", required=True, help="Canonical memory path")
    dump_parser.add_argument("--output", required=True, help="Output dump file")
    dump_parser.set_defaults(func=_cmd_memory_dump)

    image_parser = memory_subparsers.add_parser(
        "patch-card-image", help="Patch one card artwork from an input image"
    )
    image_parser.add_argument("--rom", required=True, help="Input ROM file")
    image_parser.add_argument("--card-id", type=int, required=True, help="Card ID to patch")
    image_parser.add_argument("--image", required=True, help="Input image file")
    image_parser.add_argument("--output", required=True, help="Output ROM file")
    image_parser.set_defaults(func=_cmd_memory_patch_card_image)

    string_parser = memory_subparsers.add_parser(
        "patch-string", help="Patch a string entry in a canonical string table"
    )
    string_parser.add_argument("--rom", required=True, help="Input ROM file")
    string_parser.add_argument(
        "--table",
        required=True,
        choices=sorted(CANONICAL_STRING_TABLES.keys()),
        help="String table name",
    )
    string_parser.add_argument("--index", required=True, type=int, help="String index")
    string_parser.add_argument("--text", required=True, help="New text value")
    string_parser.add_argument("--output", required=True, help="Output ROM file")
    string_parser.set_defaults(func=_cmd_memory_patch_string)

    sprites_parser = subparsers.add_parser("sprites", help="Sprite extraction utilities")
    sprites_subparsers = sprites_parser.add_subparsers(dest="sprites_command")

    extract_cards_parser = sprites_subparsers.add_parser(
        "extract-cards", help="Extract all high-resolution card artworks"
    )
    extract_cards_parser.add_argument("--rom", required=True, help="Input ROM file")
    extract_cards_parser.add_argument("--output-dir", required=True, help="Directory for extracted images")
    extract_cards_parser.set_defaults(func=_cmd_sprites_extract_cards)

    patch_card_parser = sprites_subparsers.add_parser(
        "patch-card", help="Patch one high-resolution card artwork from an input image"
    )
    patch_card_parser.add_argument("--rom", required=True, help="Input ROM file")
    patch_card_parser.add_argument("--card-id", type=int, required=True, help="Card ID to patch")
    patch_card_parser.add_argument("--image", required=True, help="Input image file")
    patch_card_parser.add_argument("--output", required=True, help="Output ROM file")
    patch_card_parser.set_defaults(func=_cmd_sprites_patch_card)

    extract_duelists_parser = sprites_subparsers.add_parser(
        "extract-duelists", help="Extract all duelist sprite variations"
    )
    extract_duelists_parser.add_argument("--rom", required=True, help="Input ROM file")
    extract_duelists_parser.add_argument(
        "--output-dir", required=True, help="Directory for extracted images"
    )
    extract_duelists_parser.set_defaults(func=_cmd_sprites_extract_duelists)

    extract_locations_parser = sprites_subparsers.add_parser(
        "extract-locations", help="Extract academy location thumbnails"
    )
    extract_locations_parser.add_argument("--rom", required=True, help="Input ROM file")
    extract_locations_parser.add_argument(
        "--output-dir", required=True, help="Directory for extracted images"
    )
    extract_locations_parser.set_defaults(func=_cmd_sprites_extract_locations)

    patch_duelist_parser = sprites_subparsers.add_parser(
        "patch-duelist", help="Patch one duelist sprite variation from an input image"
    )
    patch_duelist_parser.add_argument("--rom", required=True, help="Input ROM file")
    patch_duelist_parser.add_argument(
        "--duelist-index", required=True, type=int, help="Duelist sprite set index"
    )
    patch_duelist_parser.add_argument(
        "--variation-index", required=True, type=int, help="Sprite variation index"
    )
    patch_duelist_parser.add_argument("--image", required=True, help="Input image file")
    patch_duelist_parser.add_argument("--output", required=True, help="Output ROM file")
    patch_duelist_parser.set_defaults(func=_cmd_sprites_patch_duelist)

    patch_location_parser = sprites_subparsers.add_parser(
        "patch-location", help="Patch one academy location thumbnail from an input image"
    )
    patch_location_parser.add_argument("--rom", required=True, help="Input ROM file")
    patch_location_parser.add_argument(
        "--period", required=True, choices=LOCATION_PERIODS, help="Time of day variant"
    )
    patch_location_parser.add_argument(
        "--location-index", required=True, type=int, help="Academy location index"
    )
    patch_location_parser.add_argument("--image", required=True, help="Input image file")
    patch_location_parser.add_argument("--output", required=True, help="Output ROM file")
    patch_location_parser.set_defaults(func=_cmd_sprites_patch_location)

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
