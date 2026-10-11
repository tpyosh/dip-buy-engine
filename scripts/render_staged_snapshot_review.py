"""Compatibility entry point; use the shared independent review generator."""

from __future__ import annotations

import sys

from monthly_limit_order_review.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["generate-review-prompt", *sys.argv[1:]]))
