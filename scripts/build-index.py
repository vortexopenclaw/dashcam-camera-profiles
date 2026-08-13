#!/usr/bin/env python3
"""Validate canonical profiles and build the static browser data index."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "profiles"
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "cameras.json"
PRIVATE_PATTERNS = {
    "local or personal filesystem path": re.compile(r"/(?:Volumes|Users|home)/"),
    "submission identifier": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    "private IPv4 address": re.compile(r"(?<![a-z0-9])(?:192\.168|10|172\.(?:1[6-9]|2[0-9]|3[01]))(?:\.[0-9]{1,3}){2,3}(?![a-z0-9])", re.I),
    "private owner name": re.compile(r"\bAriel(?:\s+Bravy)?\b", re.I),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
}
REQUIRED_KEYS = {
    "$schema", "schema_version", "id", "manufacturer", "model", "evidence",
    "channel_variants", "recording", "filename_patterns", "video_samples",
    "technical_facts", "sources", "notes",
}
EVIDENCE_LEVELS = {"card-validated", "manual-backed", "technical-sample", "catalog-hint"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(profile: dict, path: Path) -> None:
    require(set(profile) == REQUIRED_KEYS, f"{path.name}: unexpected or missing top-level keys")
    require(profile["schema_version"] == "1.0", f"{path.name}: unsupported schema version")
    require(profile["id"] == path.stem, f"{path.name}: id must match filename")
    require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", profile["id"])), f"{path.name}: invalid id")
    require(profile["manufacturer"].strip() and profile["model"].strip(), f"{path.name}: camera identity missing")
    require(profile["evidence"].get("level") in EVIDENCE_LEVELS, f"{path.name}: invalid evidence level")
    recording = profile["recording"]
    require(set(recording) == {"driving_folders", "parking_folders", "other_folders", "parking_modes"}, f"{path.name}: recording shape invalid")
    for source in profile["sources"]:
        parsed = urlparse(source.get("url", ""))
        require(parsed.scheme in {"http", "https"} and bool(parsed.netloc), f"{path.name}: invalid source URL")
    serialized = json.dumps(profile, sort_keys=True)
    for label, pattern in PRIVATE_PATTERNS.items():
        require(not pattern.search(serialized), f"{path.name}: contains {label}")


def build() -> dict:
    profiles = []
    seen_ids = set()
    for path in sorted(PROFILE_DIR.glob("*.json")):
        profile = json.loads(path.read_text(encoding="utf-8"))
        validate(profile, path)
        require(profile["id"] not in seen_ids, f"duplicate profile id: {profile['id']}")
        seen_ids.add(profile["id"])
        profiles.append(profile)
    require(bool(profiles), "No canonical profiles found")
    profiles.sort(key=lambda item: (item["manufacturer"].lower(), item["model"].lower()))
    return {
        "schema_version": "1.0",
        "generated_from": "profiles/*.json",
        "camera_count": len(profiles),
        "profile_count": sum(not item["id"].startswith("metadata-only-") for item in profiles),
        "technical_sample_only_count": sum(item["id"].startswith("metadata-only-") for item in profiles),
        "cameras": profiles,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Validated and indexed {payload['camera_count']} camera references")


if __name__ == "__main__":
    main()
