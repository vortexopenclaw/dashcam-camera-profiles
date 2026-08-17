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

The browser also provides a driving-video comparison view. It filters only
measured driving samples by camera role, resolution, and individual frame-rate
values, with an optional additional-camera requirement, then sorts the matches
by the highest observed bitrate. Companion matching is restricted to samples
with the same recorded configuration, so measurements from unrelated 1CH, 2CH,
or 3CH captures are never combined. A second front-facing camera is a distinct
role, such as telephoto front, and cannot be selected as a duplicate of the
primary front camera. Parking samples remain excluded deliberately because
their bitrate is not comparable to normal driving recording. Settings such as
HDR or quality mode are shown only when the evidence records them; the frontend
never infers their effect.

When the library has no explicitly selected camera, the lower reference panel
shows a chart of the current measured-driving comparison rather than silently
defaulting to the first alphabetical profile. The chart is a visual comparison
of observed bitrate values or ranges. Its bar scale may use the upper end of a
recorded range for drawing and ordering, but it never calls that value a
manufacturer maximum or a high-quality preset. Those labels require a captured
setting in the evidence. Selecting a camera intentionally replaces the chart
with that camera's full reference page.

## Selector availability (2026-08-17)

Vueroid H1 is retained as non-public research and an auto-detection profile,
but is hidden from the Dashcam Offloader's manual model selector until it has a
public release. This avoids offering an unreleased camera as a user-selectable
product while preserving its evidence for a real card that might be scanned.

**Success checks:** H1 does not appear in manual model choices, while an exact
H1 card signature remains detectable. The static reference starts in the
comparison overview, and an explicit camera selection still opens that
camera's full detail.

**Rollback:** Remove the selector exclusion to restore H1 to manual choices,
or clear the selected-camera state only if the overview behavior must be
reverted. Neither action changes the canonical H1 profile or recorded video
facts.

## Acceptance checks

- Every canonical profile passes structural and privacy validation.
- Profile IDs and filenames are unique and stable.
- The generated index exactly matches the canonical profiles.
- Representative cameras preserve driving and parking filename/folder behavior,
  measured bitrate data, and manual links.
- Frontend JavaScript parses and the static site serves without missing assets.
- No public deployment occurs until explicitly approved.

## Public deployment decision (2026-08-17)

GitHub Pages publishes `main` from `/docs` as the first public deployment.
GitHub remains the canonical source for reviewed profiles, browser code, issue
discussion, and contributions. The public site is static and has no server,
account system, analytics, or ongoing hosting layer. A custom Vortex URL may
be considered later, but is outside this launch.

## Temporary tailnet preview (2026-08-15)

**Objective:** Make the unpublished static browser available to its authorized
tailnet viewer without exposing it to the public internet or disturbing the existing
Tailscale service on port 8443.

**Approach:** A dedicated loopback-only static server listens on port 8006.
Tailscale Serve maps only `/dashcam-camera-profiles` on the existing tailnet-only HTTPS
endpoint to that server.

**Success checks:** The local server returns the comparison UI, and the
tailnet URL returns that same UI while the root 8443 route remains configured.

**Risk and rollback:** This is internal tailnet access, not a public deploy.
Remove only the `/dashcam-camera-profiles` handler and unload the dedicated launch agent to
roll it back; do not reset the shared Tailscale Serve configuration.
