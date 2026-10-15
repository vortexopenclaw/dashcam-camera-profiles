# Parking-mode power comparison

Browse the [public comparison](https://vortexopenclaw.github.io/dashcam-camera-profiles/parking-mode.html). Download the [JSON](../docs/data/parking-measurements.json) or [CSV](../docs/data/parking-measurements.csv) for independent analysis.

## What one row means

A row is one reported measurement for a specific camera, firmware, connected/active camera configuration, parking mode, and operating state. It is not a universal product specification. Testers remain separate: Vortex Radar, rcg530, and manufacturer VIOFO-Support are not interchangeable sources. Firmware left blank by the tester remains unknown. Older firmware is not discarded simply because newer firmware exists.

The comparison records source-reported watts and milliamps separately. It never overwrites a reported watt figure with a recomputation. If only current and an explicitly stated supply voltage are available, a derived watt figure is labeled in the notes. Unknown voltage is not assumed to be 12 V or 12.6 V. Current alone cannot establish which camera consumes less power when measurement voltages differ.

Vortex Radar's sheet has a column named **Parking Voltage**. Its meaning as test-supply voltage versus a parking-related setting is not yet documented. Values are retained as `reported_parking_voltage_v` and in notes, not silently used for electrical conversions. Startup times from that sheet are retained in `reported_startup_seconds`, separately from impact-to-first-frame `wake_seconds`, because its exact timing methodology is not yet documented.

Reported minimum/maximum values stay together as one range, with `current_ma_min`/`current_ma_max` or `power_w_min`/`power_w_max`. A range endpoint is not presented as an average; range-only results have no scalar power bar or invented midpoint.

## Functional categories

Brand names remain visible alongside these cross-brand categories:

- **Impact-triggered standby (`impact-sleep`):** Waits for an impact with reduced camera activity. Includes differing quick-start versus minimum-power options; read the source mode and notes. This does not imply the same wake time or pre-event coverage across products.
- **Buffered event monitoring (`buffered-event`):** Monitors for events while retaining video from before a trigger. Often higher power because imaging/encoding remains active. Buffer duration is separate and may be unknown.
- **Unbuffered event monitoring (`unbuffered-event`):** Event monitoring without an established pre-event buffer. Not automatically equivalent to impact-only sleep.
- **Time-lapse (`time-lapse`):** Ongoing low-frame-rate recording, not idle waiting for an event. Capture frame rate can differ from playback frame rate.
- **Low-bitrate recording (`low-bitrate`):** Ongoing recording with reduced bitrate, not event-only standby.
- **Radar-assisted (`radar`):** Radar-assisted detection/wake behavior. Hardware coverage and buffer behavior vary; power alone cannot establish equivalence.
- **Hybrid (`hybrid`):** Concurrent or staged functions that cannot be represented faithfully by one of the above. Source notes explain the combination.
- **Unclassified (`unknown`):** Available evidence is insufficient to establish functional equivalence. A similar marketing name is not enough.

These are comparison aids, not claims of identical functionality. Impact sensitivity, motion detection coverage, night vision, pre-buffer length, wake latency, active cameras, cellular connectivity, and post-event time awake can all differ.

## Operating state is independent of mode

- `monitoring`: waiting for an event in the stated mode; use a settled standby figure when the source identifies one.
- `event-recording`: after a trigger; secondary to the primary monitoring comparison.
- `time-lapse`: actively recording time-lapse.
- `continuous`: ongoing recording, including low-bitrate parking recording.

Normal driving and powered-off figures are not included. A dormant interior IR emitter is not the same as an unplugged or disabled interior camera. Installed camera count and identified active views are recorded separately; unspecified views are not guessed.

## Evidence and revisions

Every numeric row links to the source sheet/post and, when applicable, the original full-size chart. Images remain hosted by their original publisher; linking them does not relicense the images. Extracted factual measurements are shared under this repository's CC BY 4.0 terms with attribution. rcg530 data is included with permission reported by Vortex Radar.

Historical/prototype results remain labeled. Explicit corrections are retained as superseded or explained in source-review notes. Tentative values flagged by the tester remain provisional, excluded from the default comparison. A chart or source that could not be transcribed confidently remains in the source index instead of being filled with guessed data.

Historical discovery covered all discovered pages of 51 rcg530-authored threads and indexed 1,313 unique posts. It is **not an exhaustive search of his account**: member/author history endpoints require login or return access errors, so undiscovered threads and replies may remain.

## Runtime estimates

A low idle power figure is not a measured battery runtime. A calculation using usable watt-hours divided by watts would assume a constant load. Impact-only modes can spend appreciable time awake after triggers; actual runtime also depends on activity, voltage cutoff, battery condition, temperature, and conversion losses. The comparison therefore does not turn idle power into an unconditional runtime promise.

## Maintenance

Canonical files:

- `measurements.json`: source-supported numeric rows.
- `sources.json`: reviewed source index, including duplicates and unresolved charts.
- `metadata.json`: discovery coverage boundary and dataset update date.

Run `python3 scripts/build-parking-data.py` to validate and regenerate the public JSON/CSV, then `python3 scripts/verify-parking.py` and `node scripts/verify-parking-frontend.js`. The Google Sheet is an input, not overwritten by this build. Add new tests as separate rows, preserve attribution and firmware, and use null for unknown values.
