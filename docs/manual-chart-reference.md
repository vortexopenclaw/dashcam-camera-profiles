# Local reported chart reference

The parking chart builder accepts one optional, chart-only reported power claim.
It never imports the claim into the public measurement database or submits it to
an API. It labels the row and exported chart **Reported / not independently
measured**, including with `details=0`.

## Fragment schema

Use the URL fragment, never the query string, for the name and value:

```text
#reference=%7B%22name%22%3A%22Example%20Cam%22%2C%22watts%22%3A0.123%7D
```

The decoded JSON must be exactly one object with these two fields:

```json
{"name":"Example Cam","watts":0.123}
```

- `name`: a trimmed, nonempty string, at most 80 UTF-16 code units. Control
  characters and directional override/isolation characters are rejected.
- `watts`: a finite JSON number between 0 and 100, inclusive. Zero is valid.
- No arrays, extra fields, extra references, or record overrides are accepted.
- The entire fragment is limited to 2,048 characters before decoding.
- Malformed references produce a generic warning and leave normal charts usable.

The reference's stable chart-only ID is `manual-reported-reference`. For an
explicit `selection=1` link, append `id=manual-reported-reference` alongside the
existing selected measurement IDs. Without an explicit selection, a valid
reference is added to the default selection when eligible.

Use `highlight=manual-reported-reference` to highlight the reference. The builder
keeps this placeholder in the query when the reference is highlighted, rather
than copying its name out of the fragment. Existing model highlights still work.

Example construction in a local browser console or application, with a chart URL
that already contains the desired public IDs:

```javascript
const url = new URL('https://vortexopenclaw.github.io/dashcam-camera-profiles/parking-charts.html?group=low-power&family=low-power&condition=monitoring&metric=watts&format=video');
// If url.searchParams.has('selection'), retain every existing id and append:
if (url.searchParams.has('selection')) url.searchParams.append('id', 'manual-reported-reference');
url.searchParams.set('highlight', 'manual-reported-reference');
url.hash = 'reference=' + encodeURIComponent(JSON.stringify({name: 'Example Cam', watts: 0.123}));
// Use url.href locally; do not submit a private reference to an external service.
```

The row is eligible only for watts, low-power monitoring, and matching all-mode
views. It has no inferred current, voltage, channels, firmware, date, wake timing,
or source URL. Switching to an incompatible metric or state removes it from the
selection, just as unsupported public rows are removed. Returning to watts does
not silently reselect it; check its picker entry or reopen the original link.

## Privacy boundaries

Fragments are not sent in ordinary HTTP requests. Copy share link preserves the
fragment, and reload, back, forward, and fragment navigation restore it locally.
This is **not encryption or secret storage**. Names and values remain visible to
anyone with the link, the browser history, browser extensions, and page scripts.
Downloaded SVG metadata and CSV include the claim; PNG and SVG visibly display
it. Do not paste a sensitive link into a public issue, URL shortener, analytics
service, screenshot, or shared document. No private values belong in repository
fixtures or documentation.

## Regression checks

```sh
node scripts/verify-parking-reference.js
python3 scripts/verify-parking-reference-browser.py --output-dir /path/to/private-artifacts
python3 scripts/verify-parking-reference-browser.py --browser webkit --output-dir /path/to/private-artifacts
```

The browser test also accepts `--url` for the published builder. Fixtures use only
fictional Example Cam claims. Tests exercise real downloads (1920×1080 SVG and
3840×2160 PNG), the visible qualification, IDs/values/metadata, inert text, zero,
malformed input, pickers, highlights, clipboard, history, and absence of fragment
data in network requests. The regular nine-ID SVG must match the pre-feature
renderer byte for byte.
