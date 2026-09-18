#!/usr/bin/env python3
"""Fail-closed audit for current StillPoint release identity and custody metadata."""
from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()
EXPECTED_VERSION = "0.4.0a2"
EXPECTED_REPOSITORY = "FortCollinsBarber-netizen/StillPoint-Core-Canonical"
EXPECTED_SCHEMA = 20
EXPECTED_PATCH = "041-icloud-auth-boundary-correction"
EXPECTED_MILESTONE = "v0.4-persistent-office-runtime-2"
EXPECTED_GOVERNANCE = "abbada7549a95510d9552441a4f7bb1c92977f899cdfa953e8e394b058d00cc9"
EXPECTED_ACCOUNT = "fortcollinsbarber@icloud.com"
EXPECTED_JURISDICTION = "personal_business"
EXPECTED_PROGRAM = "0.4-autonomous-company-os"
EXPECTED_V04_BASE = "2b3173c6783a1f0ddbac035008b970af9ee5fc7e"
EXPECTED_KERNEL1 = "9f5ed7f3cc2f030648d997a38edb195f8c9b87bb"
EXPECTED_CLASSES = ["scheduling","acknowledgement","routine_information"]
EXPECTED_DISABLED = ["bounded_outbox","gmail_send"]
EXPECTED_SERVICES = ["signal_mail:icloud","stillpointd"]
EXPECTED_TAGS = {
    "patch005-source-tree": "0c0885d7dfe88fa4f70ae265b180af4bca6945c6",
    "patch005-canonical": "4a077f216902f4bad725b6b2e61a176a54f81404",
    "v0.2.0rc1": "772ed8cb6890b5897174165e80635257e34050c7",
}
errors=[]
def require(condition,message):
    if not condition: errors.append(message)

def read_project_version(path):
    in_project=False
    for raw in path.read_text().splitlines():
        line=raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_project=line=="[project]";continue
        if in_project and line.startswith("version"):
            m=re.match(r'version\s*=\s*"([^"]+)"\s*$',line)
            if m:return m.group(1)
    return None

project_version=read_project_version(ROOT/"pyproject.toml")
init_text=(ROOT/"stillpoint"/"__init__.py").read_text()
m=re.search(r'__version__\s*=\s*"([^"]+)"',init_text)
runtime_version=m.group(1) if m else None
checkpoint=json.loads((ROOT/"CHECKPOINT.json").read_text())
manifest=json.loads((ROOT/"RELEASE_MANIFEST.json").read_text())

# A numbered patch document is a claim that canonical capability changed. The
# release identity must advance in the same change; otherwise historical metadata
# would silently govern newer code.
patch_docs=[]
for path in ROOT.glob("README_PATCH_*.md"):
    match=re.fullmatch(r"README_PATCH_(\d{3})\.md", path.name)
    if match:
        patch_docs.append(int(match.group(1)))
latest_documented_patch=max(patch_docs) if patch_docs else None

require(project_version==EXPECTED_VERSION,f"pyproject version mismatch: {project_version!r}")
require(runtime_version==EXPECTED_VERSION,f"runtime version mismatch: {runtime_version!r}")
require(checkpoint.get("version")==EXPECTED_VERSION,f"checkpoint version mismatch: {checkpoint.get('version')!r}")
require(manifest.get("version")==EXPECTED_VERSION,f"manifest version mismatch: {manifest.get('version')!r}")
require(checkpoint.get("schema_version")==EXPECTED_SCHEMA,f"checkpoint schema mismatch: {checkpoint.get('schema_version')!r}")
require(manifest.get("schema_version")==EXPECTED_SCHEMA,f"manifest schema mismatch: {manifest.get('schema_version')!r}")
require(checkpoint.get("migrations",[])[-1:] == ["020_persistent_office_runtime.sql"], "checkpoint migration tail mismatch")
require(len(checkpoint.get("migrations",[]))==EXPECTED_SCHEMA,"checkpoint migration count mismatch")
require(checkpoint.get("last_completed_milestone")==EXPECTED_MILESTONE,"checkpoint milestone mismatch")
require(manifest.get("baseline_patch")==EXPECTED_PATCH,"0.4 baseline patch mismatch")
require(manifest.get("program")==EXPECTED_PROGRAM,"0.4 manifest program mismatch")
require(checkpoint.get("program")==EXPECTED_PROGRAM,"0.4 checkpoint program mismatch")
require(manifest.get("milestone")==EXPECTED_MILESTONE,"0.4 manifest milestone mismatch")
require(checkpoint.get("git",{}).get("v04_program_base_commit")==EXPECTED_V04_BASE,"0.4 program base mismatch")
require(manifest.get("provenance",{}).get("canonical_patch041_merge")==EXPECTED_V04_BASE,"Patch 041 provenance mismatch")
require(manifest.get("provenance",{}).get("canonical_v04_kernel1_merge")==EXPECTED_KERNEL1,"Kernel 1 provenance mismatch")
require(checkpoint.get("git",{}).get("v04_kernel1_merge_commit")==EXPECTED_KERNEL1,"Kernel 1 checkpoint provenance mismatch")
require(latest_documented_patch is not None,"no numbered patch documentation found")
require(EXPECTED_PATCH.startswith(f"{latest_documented_patch:03d}-"),f"0.4 baseline trails latest earned numbered patch: {latest_documented_patch:03d}")
require(checkpoint.get("known_runtime_defects")==[],"known runtime defects are not empty")
require(manifest.get("release_invariants",{}).get("known_runtime_defects")==[],"manifest known runtime defects are not empty")
require(checkpoint.get("external_action_adapters",{}).get("production_enabled")==[],"production external adapters are enabled in checkpoint")
require(manifest.get("release_invariants",{}).get("production_external_adapters_enabled")==[],"production external adapters are enabled in release manifest")
require(checkpoint.get("production_services",{}).get("auto_started")==[],"production services are auto-started in checkpoint")
require(manifest.get("release_invariants",{}).get("production_services_auto_started")==[],"production services are auto-started in manifest")
require(checkpoint.get("external_action_adapters",{}).get("production_capable_disabled_by_default")==EXPECTED_DISABLED,"checkpoint disabled adapter capability mismatch")
require(manifest.get("release_invariants",{}).get("production_capable_disabled_by_default")==EXPECTED_DISABLED,"manifest disabled adapter capability mismatch")
require(checkpoint.get("production_services",{}).get("production_capable_not_auto_started")==EXPECTED_SERVICES,"checkpoint service capability mismatch")
require(manifest.get("release_invariants",{}).get("production_capable_services_not_auto_started")==EXPECTED_SERVICES,"manifest service capability mismatch")
require(manifest.get("release_invariants",{}).get("credentials_committed") is False,"manifest must state credentials_committed=false")
require(checkpoint.get("release_candidate",{}).get("production_activation") is False,"checkpoint must not claim production activation")
require(manifest.get("signal",{}).get("production_activation") is False,"manifest must not claim Signal production activation")
require(manifest.get("signal",{}).get("approval_evidence_committed") is False,"approval receipt must remain external evidence")

host=manifest.get("host_runtime",{})
require(host.get("platform")=="macos","production host platform mismatch")
require(host.get("service_manager")=="launchd","production host service manager mismatch")
require(host.get("service_scope")=="per-user LaunchAgent","production host scope mismatch")
require(host.get("secret_store")=="macOS Keychain","production host secret-store mismatch")
require(host.get("runs_as_root") is False,"Signal host must not run as root")
require(host.get("production_activation") is False,"release metadata must not claim production activation")
require(host.get("entrypoint")=="stillpointd","0.4 primary host entrypoint mismatch")

cp_signal=checkpoint.get("signal_governance",{})
mf_signal=manifest.get("signal",{})
require(cp_signal.get("policy_digest_sha256")==EXPECTED_GOVERNANCE,"checkpoint governance digest mismatch")
require(mf_signal.get("governance_policy_digest_sha256")==EXPECTED_GOVERNANCE,"manifest governance digest mismatch")
require(cp_signal.get("account")==EXPECTED_ACCOUNT and mf_signal.get("account")==EXPECTED_ACCOUNT,"Signal account mismatch")
require(cp_signal.get("jurisdiction")==EXPECTED_JURISDICTION and mf_signal.get("jurisdiction")==EXPECTED_JURISDICTION,"Signal jurisdiction mismatch")
require(cp_signal.get("autonomous_classes")==EXPECTED_CLASSES and mf_signal.get("autonomous_classes")==EXPECTED_CLASSES,"Signal autonomous classes mismatch")
require(cp_signal.get("mandatory_review_days")==30 and mf_signal.get("mandatory_review_days")==30,"Signal review interval mismatch")

boundaries={x.get("name"):x for x in manifest.get("production_boundaries",[])}
require(set(boundaries)=={"bounded_outbox","gmail_send","signal_mail:icloud"},"production boundary set mismatch")
icloud=boundaries.get("signal_mail:icloud",{})
require(icloud.get("auto_start") is False,"iCloud Signal service must not auto-start")
require(icloud.get("credential_env")=="STILLPOINT_ICLOUD_APP_PASSWORD","iCloud credential boundary mismatch")
require(icloud.get("requires_current_delegation") is True,"iCloud service must require current delegation")
require(icloud.get("requires_current_trigger") is True,"iCloud service must require current trigger")
require(icloud.get("requires_current_facts_snapshot") is True,"iCloud service must require current facts snapshot")

require(checkpoint.get("release_candidate",{}).get("canonical_repository")==EXPECTED_REPOSITORY,"checkpoint canonical repository mismatch")
require(manifest.get("canonical_repository")==EXPECTED_REPOSITORY,"manifest canonical repository mismatch")
require(manifest.get("runtime_capability_change") is True,"runtime capability change must be explicit")
require(manifest.get("intended_release_tag")=="v0.4.0a2","0.4 Stage 2 intended tag mismatch")

github_repository=os.environ.get("GITHUB_REPOSITORY")
if github_repository: require(github_repository==EXPECTED_REPOSITORY,f"CI repository mismatch: {github_repository}")

for tag,expected in EXPECTED_TAGS.items():
    try:
        actual=subprocess.check_output(["git","-C",str(ROOT),"rev-list","-n","1",tag],text=True,stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as exc:
        errors.append(f"cannot resolve provenance tag {tag}: {exc.output.strip()}");continue
    require(actual==expected,f"{tag} mismatch: expected {expected}, got {actual}")

if errors:
    for error in errors: print("FAIL",error)
    raise SystemExit(1)

print("Release metadata audit passed.")
print("version:",EXPECTED_VERSION)
print("repository:",EXPECTED_REPOSITORY)
print("schema:",EXPECTED_SCHEMA)
print("program:",EXPECTED_PROGRAM)
print("baseline patch:",EXPECTED_PATCH)
print("signal:",EXPECTED_ACCOUNT,EXPECTED_JURISDICTION)
