# Design

## Product goal

Maintain the community-owned technical reference for how dashcams write media.
The repository must be useful to application developers, researchers, camera
owners, and contributors without requiring Dashcam Offloader.

Each camera page should answer, when evidence exists:

- Which folders contain driving, parking, protected, manual, photo, GPS, or support data?
- How are filenames structured, and which tokens encode recording mode and channel?
- Which channel configurations have been documented or card-validated?
- What codec, resolution, frame rate, bitrate, duration, and container were measured for driving and parking recordings?
- Which claims come from a real card, an official manual, or a limited technical sample?
- Where are the official manuals and supporting research?
- What remains unknown?

## Data architecture

- `profiles/*.json` is the canonical reviewed camera dataset.
- `schemas/profile.schema.json` defines the public profile format.
- `schemas/card-scan.schema.json` defines sanitized community evidence submissions.
- `scripts/build-index.py` validates profiles and generates the browser index.
- `docs/data/cameras.json` is generated and must never be edited directly.
- `docs/` contains a static, dependency-free frontend suitable for GitHub Pages.

Profiles separate folder behavior, filename semantics, and mode-specific video
measurements. Unknown values are omitted instead of inferred from sibling
models. A measured-video-only entry is valid, but must say that its folder and
filename profile is incomplete.

## Privacy contract

No public profile, generated index, issue, or contribution may contain media,
original timestamped filenames, local paths, card names, submission IDs, GPS
coordinates, serial/device/network identifiers, credentials, or contact data.
Generation and verification fail on known private-data patterns.

## Frontend contract

The browser must work as a static site with no account, analytics, remote code,
or application runtime. It provides search and filters, then renders coverage,
driving and parking structure, filename patterns and token maps, measured video
rows, technical facts, caveats, and source links. Its content comes only from
the generated index.

## Acceptance checks

- Every canonical profile passes structural and privacy validation.
- Profile IDs and filenames are unique and stable.
- The generated index exactly matches the canonical profiles.
- Representative cameras preserve driving and parking filename/folder behavior,
  measured bitrate data, and manual links.
- Frontend JavaScript parses and the static site serves without missing assets.
- No public deployment occurs until explicitly approved.
