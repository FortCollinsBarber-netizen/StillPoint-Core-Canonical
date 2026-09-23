#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from stillpoint.calendar_core.population_artifact import (
    export_calendar_population_artifact,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    args = parser.parse_args()
    export_calendar_population_artifact(args.output)


if __name__ == "__main__":
    main()
