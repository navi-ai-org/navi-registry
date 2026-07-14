#!/usr/bin/env python3
"""One-shot migration helpers for navi-registry improvements.

- Convert legacy supports_* fields to modern attachments objects
- Optionally drop legacy fields after conversion
- Does not invent context windows or other metadata

Usage:
  python scripts/migrate_attachments.py           # dry-run report
  python scripts/migrate_attachments.py --apply   # rewrite provider files
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = ROOT / "providers"

LEGACY_MAP = {
    "supports_images": "images",
    "supports_audio": "audio",
    "supports_video": "video",
    "supports_documents": "documents",
}
LEGACY_KEYS = set(LEGACY_MAP) | {"supports_attachments"}


def migrate_model(model: dict) -> bool:
    changed = False
    attachments = dict(model.get("attachments") or {})

    for legacy, modern in LEGACY_MAP.items():
        if legacy in model:
            val = model[legacy]
            if modern not in attachments and isinstance(val, bool):
                attachments[modern] = val
                changed = True

    # supports_attachments alone does not map cleanly; ignore if no modality flags.

    if attachments and model.get("attachments") != attachments:
        model["attachments"] = attachments
        changed = True

    for key in list(LEGACY_KEYS):
        if key in model:
            del model[key]
            changed = True

    return changed


def migrate_provider(path: Path, apply: bool) -> tuple[bool, int]:
    with open(path) as f:
        data = json.load(f)

    models_changed = 0
    for model in data.get("models", []):
        if migrate_model(model):
            models_changed += 1

    if models_changed and apply:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    return models_changed > 0, models_changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    total_files = 0
    total_models = 0
    for path in sorted(PROVIDERS_DIR.glob("*.json")):
        changed, n = migrate_provider(path, args.apply)
        if changed:
            total_files += 1
            total_models += n
            action = "updated" if args.apply else "would update"
            print(f"  {action}: {path.name} ({n} models)")

    print(f"\n{total_files} files, {total_models} models {'migrated' if args.apply else 'to migrate'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
