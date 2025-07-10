""" Utility functions for loading and saving JSON files """

import json
from typing import Any

def load_json(path: str) -> Any:
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path: str, data: Any):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
