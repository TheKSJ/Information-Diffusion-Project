"""Deterministic analytical files and hashed, immutable input snapshots."""
import hashlib
import importlib.metadata
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_default(value):
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never serialize NaN as non-standard JSON.
    clean = json.loads(json.dumps(value, default=json_default), parse_constant=lambda _: None)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(clean, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path, frame, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    if frame.empty and columns is not None:
        frame = frame.reindex(columns=columns)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False, float_format="%.12g", lineterminator="\n")
    temporary.replace(path)


def read_csv(path, **kwargs):
    kwargs.setdefault("low_memory", False)
    try:
        return pd.read_csv(path, **kwargs)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def load_config(path):
    path = Path(path).resolve()
    root = path.parent.parent
    for line in (root / ".env").read_text(encoding="utf-8-sig").splitlines() if (root / ".env").exists() else []:
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["root"] = root
    config["config_path"] = path
    return config


def environment():
    names = ["numpy", "pandas", "scipy", "statsmodels", "requests", "yfinance",
             "exchange_calendars", "pyarrow", "matplotlib", "PyYAML", "tzdata"]
    return {"python": platform.python_version(), "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in names}}


def snapshot_manifest(root):
    root = Path(root)
    entries = []
    for path in sorted(root.rglob("*.meta.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        payload = path.with_name(path.name.removesuffix(".meta.json"))
        meta["path"] = payload.relative_to(root).as_posix()
        meta["hash_valid"] = payload.exists() and sha256(payload.read_bytes()) == meta["sha256"]
        entries.append(meta)
    return entries

