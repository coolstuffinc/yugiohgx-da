from .registry import ROM_LAYOUT, ASSETS


def get_region(address):
    return ASSETS.find_region_at(address)


def coverage_summary():
    categories = {}
    for r in ROM_LAYOUT:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"count": 0, "bytes": 0}
        categories[cat]["count"] += 1
        categories[cat]["bytes"] += r.size

    total = sum(c["bytes"] for c in categories.values())
    print(f"{'Category':<15} {'Count':>6} {'Bytes':>12} {'%':>8}")
    print("-" * 45)
    for cat in sorted(categories.keys()):
        c = categories[cat]
        pct = c["bytes"] / total * 100
        print(f"{cat:<15} {c['count']:>6} {c['bytes']:>12} {pct:>7.1f}%")
    print("-" * 45)
    print(
        f"{'TOTAL':<15} {sum(c['count'] for c in categories.values()):>6} {total:>12} {'100.0%':>8}"
    )


def print_map():
    print(f"{'Address':<12} {'End':<12} {'Size':>8} {'Category':<10} {'Description'}")
    print("-" * 80)
    for r in ROM_LAYOUT:
        print(
            f"0x{r.start:08X} 0x{r.end:08X} {r.size:>7}B {r.category:<10} {r.description}"
        )
