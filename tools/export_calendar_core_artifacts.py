#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from stillpoint.calendar_core.artifact_manifest import (
    export_calendar_core_artifact_manifest,
)
from stillpoint.calendar_core.projection_vectors import (
    export_calendar_projection_vectors,
)
from stillpoint.calendar_core.spec import (
    export_calendar_core_spec,
)
from stillpoint.calendar_core.population_artifact import (
    export_calendar_population_artifact,
)
from stillpoint.calendar_core.witness_overlays import (
    export_external_witness_artifact,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec-output",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--vectors-output",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
    )
    parser.add_argument(
        "--population-output",
        type=Path,
    )
    parser.add_argument(
        "--external-witness-output",
        type=Path,
    )
    args = parser.parse_args()

    export_calendar_core_spec(
        args.spec_output
    )
    export_calendar_projection_vectors(
        args.vectors_output
    )

    if args.population_output is not None:
        export_calendar_population_artifact(
            args.population_output
        )

    if args.external_witness_output is not None:
        export_external_witness_artifact(
            args.external_witness_output
        )

    if args.manifest_output is not None:
        export_calendar_core_artifact_manifest(
            args.manifest_output
        )


if __name__ == "__main__":
    main()
