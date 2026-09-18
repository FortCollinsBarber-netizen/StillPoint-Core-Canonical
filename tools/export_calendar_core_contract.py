#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from stillpoint.calendar_core.contract import export_calendar_core_contract


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    export_calendar_core_contract(args.output)


if __name__ == "__main__":
    main()
