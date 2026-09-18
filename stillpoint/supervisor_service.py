from __future__ import annotations

import argparse
import json
import os
import signal
from pathlib import Path

from .supervisor import CompanySupervisor, SupervisorConfig, OFFICE_ROLES
from .secret_custody import read_secret


def _root() -> Path:
    return Path(os.getenv("STILLPOINT_ROOT") or Path.cwd()).expanduser().resolve()


def _config(*, start_offices: bool=True) -> SupervisorConfig:
    provider=os.getenv("STILLPOINT_PROVIDER","mock").strip().lower()
    model=os.getenv("STILLPOINT_MODEL","").strip()
    if not model:
        model="grok-4.6" if provider=="xai" else "default"
    provider_api_key=None
    if provider=="xai" and (
        os.getenv("STILLPOINT_XAI_API_KEY_FD") or os.getenv("XAI_API_KEY")
    ):
        provider_api_key=read_secret(
            os.environ,
            value_name="XAI_API_KEY",
            fd_name="STILLPOINT_XAI_API_KEY_FD",
        )
    return SupervisorConfig(
        root=_root(),
        provider_name=provider,
        default_model=model,
        provider_api_key=provider_api_key,
        supervisor_interval_seconds=float(os.getenv("STILLPOINT_SUPERVISOR_INTERVAL","2")),
        worker_poll_seconds=float(os.getenv("STILLPOINT_OFFICE_POLL_SECONDS","1")),
        lease_ttl_seconds=int(os.getenv("STILLPOINT_OFFICE_LEASE_TTL_SECONDS","90")),
        heartbeat_interval_seconds=int(os.getenv("STILLPOINT_OFFICE_HEARTBEAT_SECONDS","20")),
        retry_backoff_seconds=int(os.getenv("STILLPOINT_OFFICE_RETRY_BACKOFF_SECONDS","60")),
        max_failures=int(os.getenv("STILLPOINT_OFFICE_MAX_FAILURES","3")),
        start_office_workers=start_offices,
    )


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog="stillpointd")
    sub=parser.add_subparsers(dest="cmd",required=False)
    sub.add_parser("serve")
    sub.add_parser("once")
    sub.add_parser("check")
    sub.add_parser("status")
    args=parser.parse_args(argv)
    cmd=args.cmd or "serve"

    if cmd=="status":
        path=_root()/"state"/"stillpointd_status.json"
        if not path.is_file():
            print(json.dumps({"running_evidence":False,"status_cache":None},indent=2))
            return 1
        print(path.read_text(),end="")
        return 0

    sup=CompanySupervisor(_config(start_offices=(cmd=="serve")))
    if cmd=="check":
        try:
            print(json.dumps({
                "ready":True,
                "schema_version":sup.db.schema_version,
                "root":str(sup.config.root),
                "offices":list(OFFICE_ROLES),
                "provider":sup.config.provider_name,
                "model":sup.config.default_model,
                "external_authority_granted_by_supervisor":False,
            },indent=2))
            return 0
        finally:
            sup.close()

    if cmd=="once":
        try:
            sup.acquire_singleton()
            sup.retire_prior_supervisor_workers()
            print(json.dumps(sup.tick(),indent=2,default=str))
            return 0
        finally:
            sup.close()

    def stop(_signum,_frame):
        sup.stop_event.set()

    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    sup.serve()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
