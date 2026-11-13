# Z100 Master: separate 3CH driving/time-lapse measurements

[Exact anonymous evidence](data/ddpai-z100-master-3ch-evidence.json) contains 72 canonical HEVC clips, with 64 paired native observations (not extra clips). Historical 401 probes, 19 scanner occurrences, 19 earlier owner pairs and 40 collision-test clips remain unchanged, as do the separate 2CH and 4CH power cohorts.

| Physical role | Driving-inferred | Owner-confirmed time-lapse | Video bitrate driving (bps) | Video bitrate time-lapse (bps) |
|---|---:|---:|---:|---:|
| Front, 3840×2160, nominal playback 30 FPS | 13 | 15 | 41822921–42032385 | 11685153–13433632 |
| Telephoto (inside label), 2560×1440, nominal playback 25 FPS | 13 | 0 | 8723341–9354655 | Not observed |
| Rear, 3840×2160, nominal playback 25 FPS | 13 | 18 | 29682157–29934067 | 19579192–20859455 |

The profile appends ten full-length/short groups; each of the five role/mode combinations has one short/partial clip. Full-length means video-stream playback duration >=59.9 seconds. Exact sample pairs retain file bytes, stream/container duration and bitrate, nominal/average frame rate, dimensions and frame count. These samples also feed the profile/index storage inputs; alternate native observations are not fed as extra clips.

Owner-confirmed time-lapse applies to front S_ and rear Q_ on this card. Ordinary files are driving-inferred. The pre-fix native scanner called rear Q_ Driving; this is a classifier limitation, not contradictory configured-mode evidence. No telephoto time-lapse observed does not prove universal disablement. Playback FPS is not capture cadence. No quality, HDR, elapsed coverage or power behavior is inferred.

Main UI-log identity is DDPAI DZ2602_GLOBAL_Z100 Master, software 8.0.0.23. This is scoped UI-log/owner provenance, not intrinsic per-clip metadata. Both rear_model and inside_model report DR4004 with version 9.0.0.17: protocol observations alone establish neither physical mapping nor two units. A separately reported Mini3X version is not evidence from this card. Empty pre-fix component metadata resulted from ANSI log framing and is not evidence of absence.

Only saved JSON was used for integration. Original names, timestamps, source hashes, paths and private identifiers are not published. The digest covers only anonymous numeric projection. Validate with `python3 scripts/verify-z100-3ch.py`; optional `--private-data` reads saved JSON only, never media.
