#!/usr/bin/env python3
"""Plan/apply the explicitly authorized HA media migration with writers stopped."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.media_layout import migrate, migration_plan, retire_legacy_geography

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("action", choices=("plan", "migrate", "retire-geography"))
p.add_argument("--root", type=Path, required=True)
p.add_argument("--config", type=Path, action="append", default=[])
p.add_argument("--writers-stopped", action="store_true")
p.add_argument("--consumers-verified", action="store_true")
p.add_argument("--report", type=Path, required=True)
args = p.parse_args()
if args.action == "retire-geography":
    report = retire_legacy_geography(args.root, writers_stopped=args.writers_stopped,
                                    consumers_verified=args.consumers_verified, report_path=args.report)
elif args.action == "plan":
    report = {"moves": [[str(a), str(b)] for a, b in migration_plan(args.root)]}
else:
    report = migrate(args.root, args.config, writers_stopped=args.writers_stopped)
args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"report": str(args.report), "state": report.get("state", "plan"),
                  "moves": len(report.get("moves", []))}))
