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
    t340 = next(camera for camera in cameras if camera["id"] == "viofo-t340")
    assert t340["evidence"]["level"] == "technical-sample"
    assert len(t340["video_samples"]) == 45
    for mode in ("driving", "parking"):
        samples = [sample for sample in t340["video_samples"][:8] if sample["mode"] == mode]
        assert {sample["channel"] for sample in samples} == {"front", "rear", "interior", "telephoto"}
        for sample in samples:
            assert sample["source"] == "app_submission"
            assert sample["recording_configuration"] == "4-channel: front, rear, interior, telephoto"
            assert sample["codec"] == "H.264" and sample["fps"] == "30"
            assert sample["resolution"] == ("3840x2160" if sample["channel"] == "front" else "2560x1440")
            hdr = "on" if sample["channel"] in {"front", "interior"} else "off"
            assert f"HDR {hdr}" in sample["settings_note"]
            low, high = map(float, sample["bitrate"].removesuffix(" Mbps").split("-"))
            expected = 4.095 if mode == "parking" else 31.95 if sample["channel"] == "front" else 14.33
            assert abs(low - expected) < 0.02 and abs(high - expected) < 0.02
    assert any("paired whole-file measurements" in fact["value"] for fact in t340["technical_facts"])
    newer = t340["video_samples"][8:20]
    for mode in ("driving", "protected", "parking"):
        samples = [sample for sample in newer if sample["mode"] == mode]
        assert len(samples) == 4
        assert {sample["channel"] for sample in samples} == {"front", "rear", "interior", "telephoto"}
        for sample in samples:
            assert sample["source"] == "app_submission"
            assert sample["codec"] == "H.264" and sample["fps"] == "30"
            assert "HDR and firmware not recorded" in sample["settings_note"]
            low, high = map(float, sample["bitrate"].removesuffix(" Mbps").split("-"))
            expected = 4.095 if mode == "parking" else 36.85 if sample["channel"] == "front" else 21.30
            assert abs(low - expected) < 0.06 and abs(high - expected) < 0.06
    assert all(folder["validation"] == "app_submission_sampled" for folder in t340["recording"]["driving_folders"])
    low_samples = t340["video_samples"][20:36]
    for mode in ("driving", "protected", "parking", "parking_impact_detection"):
        samples = [sample for sample in low_samples if sample["mode"] == mode]
        assert {sample["channel"] for sample in samples} == {"front", "rear", "interior", "telephoto"}
        assert len(samples) == 4
        for sample in samples:
            assert "Owner confirms Low driving bitrate" in sample["settings_note"]
            assert "not a verified trigger" in sample["settings_note"]
            minimum, maximum = map(float, sample["bitrate"].removesuffix(" Mbps").split("-"))
            expected = 4.10 if "parking" in mode else 27.04 if sample["channel"] == "front" else 11.88
            assert abs(minimum - expected) < 0.03 and abs(maximum - expected) < 0.03
    assert any("userImmutable=true" in fact["value"] for fact in t340["technical_facts"])
    maximum_three = t340["video_samples"][36:]
    assert len(maximum_three) == 9
    assert {sample["channel"] for sample in maximum_three} == {"front", "rear", "interior"}
    for sample in maximum_three:
        assert "3-channel" in sample["recording_configuration"]
        assert "Maximum driving bitrate" in sample["settings_note"]
        minimum, maximum = map(float, sample["bitrate"].removesuffix(" Mbps").split("-"))
        expected = 4.095 if "parking" in sample["mode"] else 53.23 if sample["channel"] == "front" else 27.03
        assert abs(minimum - expected) < 0.06 and abs(maximum - expected) < 0.06

    assert any(folder["path"] == "cont_rec" for folder in arc900["recording"]["driving_folders"])
    assert any(folder["path"] == "parking_rec" for folder in arc900["recording"]["parking_folders"])
    assert any(source["kind"] == "manual" for source in arc900["sources"])

    s1_qhd = next(camera for camera in cameras if camera["id"] == "vueroid-s1-qhd-infinite")
    assert s1_qhd["evidence"]["level"] == "card-validated"
    assert any(sample["channel"] == "rear" and sample["resolution"] == "2560x1440" for sample in s1_qhd["video_samples"])
    assert any(sample["mode"] == "parking time-lapse" and sample["fps"] == "5" for sample in s1_qhd["video_samples"])

    elite_9 = next(camera for camera in cameras if camera["id"] == "blackvue-elite-9")
    assert elite_9["evidence"]["level"] == "card-validated"
    assert any("overlap" in fact["value"] for fact in elite_9["technical_facts"])
    assert any(sample["mode"] == "parking impact detection" for sample in elite_9["video_samples"])

    u3000_pro = next(camera for camera in cameras if camera["id"] == "thinkware-u3000-pro")
    assert u3000_pro["evidence"]["level"] == "card-validated"
    assert any(sample["mode"] == "parking motion detection" and sample["fps"] == "15" for sample in u3000_pro["video_samples"])

    frontend = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert 'id="quality-brand"' in frontend
    assert 'id="quality-sort"' in frontend
    print("Verification passed: canonical profiles, privacy, mode-specific video, folders, filenames, and manuals")


if __name__ == "__main__":
    main()
