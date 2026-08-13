# Privacy rules for contributors

This project needs card *structure*, not your footage or identity.

## Safe to share

- Manufacturer and model, if known.
- Camera-channel setup and general role labels.
- Folder names and extension counts.
- Generalized filename patterns, such as `REC_YYYYMMDD_HHMMSS_F.MP4`.
- Aggregate clip counts and rounded size ranges.
- Codec, resolution, frame-rate, duration, and bitrate summaries read locally.
- Non-unique model and firmware strings, after reviewing them.
- Public manufacturer documentation URLs.

## Do not share publicly

- Any media file, thumbnail, audio track, screenshot, or GPS log.
- Full filenames or timestamps that could reveal where or when you drove.
- Raw filesystem paths, card names, or volume labels.
- Serial numbers, IMEI, device identifiers, MAC addresses, Bluetooth IDs,
  Wi-Fi/network names, passwords, account/cloud data, tokens, or keys.
- Full configuration files or raw settings dumps.
- License plates, faces, addresses, phone numbers, or contact details.

## How to sanitize a filename

Replace the actual date, time, sequence number, or other unique values with a
token. Keep fixed letters, separators, extension, and channel token. For
example, convert a real front clip into:

```text
REC_YYYYMMDD_HHMMSS_F.MP4
```

If a token itself might be unique, replace it with `VALUE` and explain what it
represents.

## Before publishing

Review the entire issue, pull request, diff, and attached files. Public GitHub
content is difficult to retract once copied or indexed. When in doubt, leave
the field out and ask a maintainer.
