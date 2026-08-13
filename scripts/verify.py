#!/usr/bin/env python3
"""Repository validation and generated-index freshness checks."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "data" / "cameras.json"


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        generated = Path(temp) / "cameras.json"
        subprocess.run(["python3", str(ROOT / "scripts" / "build-index.py"), "--output", str(generated)], check=True)
        if not INDEX.is_file() or generated.read_bytes() != INDEX.read_bytes():
            raise SystemExit("Generated frontend index is stale. Run python3 scripts/build-index.py")

    payload = json.loads(INDEX.read_text(encoding="utf-8"))
    cameras = payload["cameras"]
    assert payload["camera_count"] >= 67
    assert payload["profile_count"] >= 55

    dr970 = next(camera for camera in cameras if camera["id"] == "blackvue-dr970x-lte-plus")
    assert any(folder["path"] == "BlackVue/Record" for folder in dr970["recording"]["driving_folders"])
    assert any(pattern["modes"].get("P") == "parking" for pattern in dr970["filename_patterns"])
    assert any("61 Mbps" in fact["value"] for fact in dr970["technical_facts"])

    dr970_box = next(camera for camera in cameras if camera["id"] == "blackvue-dr970x-box-plus")
    assert dr970_box["evidence"]["level"] == "catalog-hint"
    assert not dr970_box["recording"]["driving_folders"]
    assert not dr970_box["filename_patterns"]
    assert any(source["kind"] == "manual" for source in dr970_box["sources"])

    a229 = next(camera for camera in cameras if camera["id"] == "viofo-a229-pro")
    assert any(sample["mode"] == "driving" and "36.0 Mbps" in sample["bitrate"] for sample in a229["video_samples"])
    assert any(sample["mode"] == "parking" and "4.1 Mbps" in sample["bitrate"] for sample in a229["video_samples"])

    arc900 = next(camera for camera in cameras if camera["id"] == "thinkware-arc-900")
    assert any(folder["path"] == "cont_rec" for folder in arc900["recording"]["driving_folders"])
    assert any(folder["path"] == "parking_rec" for folder in arc900["recording"]["parking_folders"])
    assert any(source["kind"] == "manual" for source in arc900["sources"])
    print("Verification passed: canonical profiles, privacy, mode-specific video, folders, filenames, and manuals")


if __name__ == "__main__":
    main()
