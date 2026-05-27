import json
import os
from .coverage import get_region

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_FUNCTIONS_PATH = os.path.join(_DATA_DIR, "ghidra_functions.json")
_DEFAULT_GHIDRA_URL = "http://127.0.0.1:8080"


class GhidraFunctionMap:
    def __init__(self):
        self._map: dict[int, str] = {}
        self._load()

    def _load(self):
        try:
            with open(_FUNCTIONS_PATH) as f:
                raw = json.load(f)
            self._map = {int(k, 16): v for k, v in raw.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            self._map = {}

    def save(self):
        data = {f"0x{k:08X}": v for k, v in sorted(self._map.items())}
        with open(_FUNCTIONS_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def lookup(self, address: int) -> str | None:
        return self._map.get(address)

    def lookup_hex(self, address_str: str) -> tuple[int, str | None]:
        addr = (
            int(address_str, 16)
            if address_str.startswith("0x")
            else int(address_str, 16)
        )
        return addr, self._map.get(addr)

    def stats(self) -> tuple[int, int, int]:
        total = len(self._map)
        named = sum(1 for n in self._map.values() if not n.startswith("FUN_"))
        return total, named, total - named

    def update(self, functions: list[tuple[int, str]]):
        self._map = dict(functions)
        self.save()

    def sync(self, ghidra_url: str = _DEFAULT_GHIDRA_URL) -> tuple[int, int]:
        import requests

        resp = requests.get(f"{ghidra_url}/list_functions", timeout=10)
        resp.raise_for_status()
        functions: list[tuple[int, str]] = []
        for line in resp.text.splitlines():
            line = line.strip()
            if not line or " at " not in line:
                continue
            name, _, addr_str = line.partition(" at ")
            addr_str = addr_str.strip()
            if addr_str.startswith("0x"):
                addr_str = addr_str[2:]
            addr = int(addr_str, 16)
            functions.append((addr, name))
        old_count = len(self._map)
        self._map = dict(functions)
        self.save()
        return len(self._map), len(self._map) - old_count


def lookup_address(address: int) -> dict:
    region = get_region(address)
    fmap = GhidraFunctionMap()
    name = fmap.lookup(address)
    return {
        "address": f"0x{address:08X}",
        "function": name or "(none)",
        "region": region.name if region else "(none)",
        "category": region.category if region else "",
        "description": region.description if region else "",
    }
