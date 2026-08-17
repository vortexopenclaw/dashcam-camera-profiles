# Contributing a dashcam card scan

Thank you. A small structural scan can make a camera work better for everyone.

## Fast path

1. Copy `examples/card-scan.example.json`.
2. Fill in the known manufacturer, model, camera setup, and any official
   manual URL.
3. Describe the card with generalized folder names and filename *patterns*.
4. Validate it against `schemas/card-scan.schema.json`.
5. Open an issue or pull request with the sanitized JSON.

If you have no technical experience, open an issue with the camera model,
channel layout, and manual link. A maintainer can help turn that into a scan.

## Editing a camera profile

Reviewed reference data lives in `profiles/`, with one JSON document per
camera following `schemas/profile.schema.json`. Keep observations tied to an
evidence level and preserve unknown fields as empty arrays instead of copying
behavior from a similar model.

After editing a profile, run:

```sh
python3 scripts/build-index.py
python3 scripts/verify.py
bash scripts/privacy-audit.sh
node --check docs/assets/app.js
```

Commit both the profile and the regenerated `docs/data/cameras.json` index.

## Keep the distinction clear

Separate what the card showed from what the manual says. A manual can
document a feature that was disabled on the submitted card. A scan can show a
real filename pattern that a manual omits. Both are useful, but they are not
the same evidence.

## Review process

Maintainers will:

1. Check that the submission is safe to publish.
2. Confirm model identity and cited sources.
3. Compare the scan with existing profiles and other card evidence.
4. Publish only generalized data, with an appropriate evidence level.

Submitted scans are evidence, not automatic profile changes. A new profile is
reviewed before it is accepted as a reusable rule.

## Good contributions

- A new or corrected folder name, including exact case.
- A generalized filename pattern and the channel/mode it represents.
- Technical summaries such as codec, dimensions, frame rate, bitrate range,
  and duration range, without uploading the clip.
- A manual URL and a note identifying which behavior it documents.
- Confirmation of which cameras were physically connected when the card was
  recorded.

### Examples that help reviewers

- **Folder correction:** “`Parking` is the exact observed folder name; it is
  not `parking`.” Include the evidence level and a manual link if one exists.
- **Filename rule:** Record a generalized pattern such as
  `REC_YYYYMMDD_HHMMSS_R.MP4`, then identify which fixed token means rear and
  which recording mode it appeared in. Do not include the original filename.
- **Measured video:** “Front, 3840x2160 at 30 FPS, H.265, 52-56 Mbps, MP4;
  2-channel front and rear configuration; HDR off.” If a setting was not
  recorded, write that it is unknown rather than guessing.
- **Manual evidence:** Link the exact official manual or support page and say
  which claim it supports. A manual can establish a capability without proving
  it was enabled on a particular card.

The JSON example is intentionally synthetic. It demonstrates the shape of a
safe contribution, not a real camera claim.

## Never put private material in GitHub

Read [docs/privacy.md](docs/privacy.md) before opening an issue or pull
request. If unsure, omit the field and say it was omitted for privacy.
