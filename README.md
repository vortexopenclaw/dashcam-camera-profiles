# Dashcam Camera Profiles

An open, community-maintained reference for dashcam card layouts, recording
conventions, and privacy-preserving card scans.

This repository is useful whether or not you use Dashcam Offloader. Its goal
is to make real, documented camera evidence reusable by any open tool.

## Browse the reference

The static browser in `docs/` makes the technical data readable without
installing an app. It includes searchable camera pages for folder structures,
filename rules, driving and parking behavior, measured codec/resolution/FPS/
bitrate data, manuals, evidence levels, and known gaps.

To preview it locally:

```sh
python3 -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`. The browser has no account system,
analytics, cookies, or runtime dependencies.

## Contribute a card scan

You do **not** need to own or install Dashcam Offloader to contribute.

1. Read [the privacy guide](docs/privacy.md).
2. Create a JSON file that follows [the card-scan schema](schemas/card-scan.schema.json).
3. Start from [the example](examples/card-scan.example.json), remove anything
   identifying, and open an issue or pull request.

For now, non-technical contributors can also send a sanitized scan package to
the Dashcam Offloader project through its in-app **Learn Card** workflow. A
standalone scanner and browser upload flow are planned; neither is required to
participate in this repository.

## What belongs here

- Reviewed camera profiles, with their evidence level and sources.
- Sanitized, structural card scans that help validate those profiles.
- Official manual or product-page links that support documented behavior.
- Corrections to folder names, filename patterns, channels, recording modes,
  codecs, resolutions, and parking behavior.

## What must never be submitted

- Video, photo, thumbnail, audio, GPS, or route data.
- Serial numbers, device IDs, MAC/Bluetooth IDs, Wi-Fi names or passwords,
  accounts, tokens, and full configuration dumps.
- Personal folder paths, volume labels, original filenames, license plates,
  or contacts in a public pull request or issue.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the review process.

## Evidence levels

- `card-validated`: a sanitized real-card scan has confirmed the behavior.
- `manual-backed`: official documentation supports it, but a card has not yet
  validated it.
- `catalog-hint`: a model is known to exist, but layout-specific support is
  not claimed.

An evidence level is a boundary, not a quality score. A profile does not claim
unobserved behavior simply because a similar model has it.

## Repository layout

- `schemas/` - stable public formats for scan and profile data.
- `examples/` - synthetic examples safe to copy and modify.
- `profiles/` - the canonical, reviewable technical profile for each camera.
- `docs/` - the generated data index, searchable frontend, and privacy guide.
- `scripts/` - deterministic import, validation, privacy, and index tooling.

## Status

The repository currently contains 67 camera references: 55 camera profiles
with card, manual, or catalog evidence, plus 12 references built from measured
video metadata where the card layout is not yet known. Missing information is
shown as missing rather than inferred from a related model.

Run `python3 scripts/verify.py` before submitting a profile change. It checks
the canonical profiles, regenerated browser index, representative driving and
parking data, filenames, folder layouts, manuals, and privacy boundaries.

## License

Data in this repository is licensed under [CC BY 4.0](LICENSE). Code or tools
that consume it keep their own licenses.
