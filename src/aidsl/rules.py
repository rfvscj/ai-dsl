from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


_RULES_DIR = Path(__file__).with_name("rules")


@lru_cache(maxsize=None)
def load_rules(name: str) -> Dict[str, Any]:
    path = _RULES_DIR / f"{name}.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_python_rules() -> Dict[str, Any]:
    return load_rules("python_aidl_rules")
