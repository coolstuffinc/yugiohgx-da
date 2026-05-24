import argparse
import sys

from .memory_map import CANONICAL_STRING_TABLES, list_memory_paths
from .memory_ops import dump_region, patch_card_image, patch_string_entry


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
