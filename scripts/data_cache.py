"""Simple Parquet-backed cache with TTL.

Design:
- Key: a string like 'tushare_income_600519.SH_ann_20250430'
- Stores DataFrame + metadata (fetch time) in a Parquet file
- Stale entries (> CACHE_TTL_DAYS) are ignored (caller re-fetches)
- No LRU eviction — disk is cheap, and we prune only if a reset is needed.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from . import config

_META_SIDECAR_SUFFIX = ".meta.json"


def _meta_path(p: Path) -> Path:
    return p.with_suffix(p.suffix + _META_SIDECAR_SUFFIX)


def get(key: str) -> Optional[pd.DataFrame]:
    """Return cached DataFrame if fresh, else None."""
    p = config.cache_path(key)
    mp = _meta_path(p)
    if not (p.exists() and mp.exists()):
        return None
    try:
        meta = json.loads(mp.read_text())
        fetched_at = dt.datetime.fromisoformat(meta["fetched_at"])
    except Exception:
        return None
    age = dt.datetime.now() - fetched_at
    if age.total_seconds() > config.CACHE_TTL_DAYS * 86400:
        return None
    try:
        return pd.read_parquet(p)
    except Exception:
        return None


def put(key: str, df: pd.DataFrame, extra: dict[str, Any] | None = None) -> None:
    """Store a DataFrame with current timestamp."""
    if df is None:
        return
    if len(df) == 0:
        # 仍然存空表，避免空结果重复打接口；标记为 empty=True
        pass
    p = config.cache_path(key)
    df.to_parquet(p, index=False)
    meta = {
        "key": key,
        "fetched_at": dt.datetime.now().isoformat(timespec="seconds"),
        "rows": len(df),
        "cols": list(df.columns),
    }
    if extra:
        meta.update(extra)
    _meta_path(p).write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def invalidate(key: str) -> bool:
    """Delete cache entry for a key. Return True if deleted."""
    p = config.cache_path(key)
    mp = _meta_path(p)
    deleted = False
    for f in (p, mp):
        if f.exists():
            f.unlink()
            deleted = True
    return deleted


def info(key: str) -> dict[str, Any] | None:
    """Return cache metadata for a key if present."""
    mp = _meta_path(config.cache_path(key))
    if not mp.exists():
        return None
    try:
        return json.loads(mp.read_text())
    except Exception:
        return None
