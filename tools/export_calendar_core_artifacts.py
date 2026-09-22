#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from stillpoint.calendar_core.projection_vectors import export_calendar_projection_vectors
from stillpoint.calendar_core.spec import export_calendar_core_spec


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec-output", required=True, type=Path)
    parser.add_argument("--vectors-output", required=True, type=Path)
    args = parser.parse_args()
    export_calendar_core_spec(args.spec_output)
    export_calendar_projection_vectors(args.vectors_output)


if __name__ == "__main__":
    main()
