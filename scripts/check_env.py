"""Environment sanity check — run before any collector to diagnose missing pieces.

Usage:
    python3 -m scripts.check_env
"""
from __future__ import annotations

import importlib
import sys

REQUIRED_PKGS = ["tushare", "yfinance", "pypdf", "pandas", "pyarrow", "requests"]


def check() -> int:
    """Return 0 if env is OK, non-zero otherwise."""
    from . import config

    print("=== company-analysis skill env check ===\n")
    ok = True

    # Python
    print(f"Python: {sys.version.split()[0]}")

    # Packages
    print("\nRequired packages:")
    for pkg in REQUIRED_PKGS:
        try:
            m = importlib.import_module(pkg)
            ver = getattr(m, "__version__", "?")
            print(f"  [OK] {pkg} {ver}")
        except ImportError:
            print(f"  [MISSING] {pkg}  → pip3 install --user {pkg}")
            ok = False

    # Token
    print("\nTushare token:")
    if config.TUSHARE_TOKEN:
        masked = config.TUSHARE_TOKEN[:4] + "…" + config.TUSHARE_TOKEN[-4:]
        print(f"  [OK] TUSHARE_TOKEN set (length={len(config.TUSHARE_TOKEN)}, masked={masked})")
    else:
        print("  [MISSING] TUSHARE_TOKEN not set")
        print("  → Add to ~/.zshrc:  export TUSHARE_TOKEN='your_token_here'")
        print("  → A 股 / 港股 collector 将无法工作（美股 yfinance 不受影响）")
        ok = False

    # Cache dir
    print(f"\nCache: {config.CACHE_DIR}  (TTL={config.CACHE_TTL_DAYS} days)")
    print(f"Output: {config.OUTPUT_ROOT}")

    print("\n" + ("✅ All checks passed." if ok else "⚠️  Fix the [MISSING] items above."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(check())
