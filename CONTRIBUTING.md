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

## Keep the distinction clear

Separate what the card actually showed from what the manual says. A manual can
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

## Never put private material in GitHub

Read [docs/privacy.md](docs/privacy.md) before opening an issue or pull
request. If unsure, omit the field and say it was omitted for privacy.
