#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from stillpoint.providers.xai import XAIProvider

def probe(api_key: str, model: str, *, provider_factory=None):
    key=str(api_key or "").strip()
    if not key:
        raise RuntimeError("empty xAI API key")
    factory=provider_factory or XAIProvider
    provider=factory(timeout_seconds=60,api_key=key,default_model=model)
    return provider.generate(
        system="StillPoint 0.4 production provider capability preflight.",
        prompt="Return OK.",
        model=model,
        tools=[],
        effort="low",
        max_output_tokens=32,
        task_id="stillpointd-provider-preflight",
        phase="provider_capability_probe",
    )

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--model",default="grok-4.6")
    args=parser.parse_args(argv)
    key=sys.stdin.read().strip()
    try:
        probe(key,args.model)
    except Exception as exc:
        print(f"xAI capability preflight failed: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 1
    print(f"xAI credential/model capability verified: {args.model}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
