# Z100 Master: separate collision-test video cohort

The [anonymous evidence](data/ddpai-z100-master-evidence.json), under
`collision_test_scan`, adds **40 measured clips: 20 front and 20 telephoto**.
The owner confirms the main-unit two-view setup and collision-detection parking
that wakes, records, then sleeps. Some driving footage remains on this card.
All individual driving/parking modes and trigger causes are therefore unresolved;
ordinary filenames without the earlier parking marker do not resolve them.
This cohort does not change earlier time-lapse or historical mode attribution.

| Physical view | Playback length | Clips | Video-stream bitrate (Mbps) |
| --- | --- | ---: | ---: |
| Front, 3840×2160, 30 fps | Full-length | 16 | 41.827141–41.985778 |
| Front, 3840×2160, 30 fps | Short/partial | 4 | 41.923810–42.034223 |
| Telephoto, 2560×1440, 25 fps | Full-length | 16 | 8.395097–9.753787 |
| Telephoto, 2560×1440, 25 fps | Short/partial | 4 | 8.422113–9.386858 |

All 40 headers identify HEVC. Full-length means video playback duration at least
59.9 seconds. Short clips remain in the evidence rather than being discarded.
The evidence preserves exact per-clip file bytes, video duration, video bitrate,
dimensions, rational nominal and average playback FPS, video frame count,
container duration and container bitrate. Container and video rates are not
interchangeable. Header probes do **not** establish full-file decode validity.

## Source correspondence and counting

- Each actual clip has one canonical ffprobe observation and one paired
  AVFoundation observation. These are **40 clips, not 80 independent clips**.
- Native observations were linked through retained private per-sample paths.
  The real offline receiving-Worker stored-record round trip preserved all 40
  native measurements and their private identity links.
- All **15 original submitted occurrences** (8 front, 7 telephoto) remain intact,
  in source group and occurrence order. Each uniquely matches an actual clip
  by channel context and exact same-producer six-field numeric equality. No
  independent arrays were joined by index.
- Oracle/native cross-checks require identical size and dimensions, less than
  0.0011 seconds duration difference (millisecond rounding), and less than
  0.04 fps nominal-playback difference (representation differences). The
  source-specific bitrate and duration values are retained, not overwritten.
- Anonymous `clip_index` values are numeric-evidence ordering, not source paths,
  recording timestamps, folder identities, raw source identifiers or hashes.
  The correspondence to original media stays private outside Git.
- The earlier **401 probes, 19 historical scanner occurrences and 19 separately
  retained owner-scan pairs** remain unchanged. No cross-scan physical-clip
  uniqueness or combined distinct-video total is asserted.

Four approximately five-minute two-view bursts are observable in private timing
metadata. That is not proof of four physical impacts, exact wake latency, or that
every clip is collision footage. Firmware, quality, HDR and capture cadence are
unknown. Bitrate differences do not identify a selected quality/menu setting.
The public artifact contains no original filenames, dates or private folder
identities from this cohort. No media or source-card path is needed for validation.

## Verification

Run the lightweight checks from the repository root:

```sh
python3 scripts/build-index.py
python3 scripts/verify.py
python3 scripts/verify-z100-master.py
python3 scripts/verify-z100-collision.py
python3 scripts/test-z100-collision.py
```

Maintainers may additionally pass `--private-data` to the collision validator,
pointing to the current cohort's private saved-JSON directory. This compares the
canonical probes, original submitted pairs, native snapshot and actual offline
stored record, without opening any media or paths embedded in those records.
This is database/reference evidence only, not an app recognition or release fix.
