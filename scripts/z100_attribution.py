"""Exact, scoped provenance amendment for existing Z100 recordings only.

Historical guards restore only these authorized metadata leaves, then compare
all remaining values. Never normalize measurement, configuration or null fields.
"""
from copy import deepcopy

BASELINE = '6ec74224c998878b8ac7360f9f56580efc056452'
ATTRIBUTION = {
    'contributor': 'Vortex Radar',
    'unit': 'Vortex Radar’s test unit',
    'source': 'explicit owner confirmation',
    'source_quote': 'Better. All of the recordings are off my test unit. None are anonymous or someone else',
    'scope': 'All existing Z100 Master recording batches: historical probes and scanner occurrences, separate owner scan, collision-test scan, and separate 3CH cohort. Not other models or future contributors.',
    'qualification': 'Same test unit does not establish the same configuration, firmware, mode, or cross-scan physical clip identity. No prototype or production status is inferred.',
}

# Paths are explicit: this is not a recursive string replacement or blanket
# removal of provenance fields from preservation comparisons.
VIDEO_CHANGES = [
    (('methodology', 0),
     'All successful retained video header probes are included exactly once. Anonymous technical values only; original media and audit records remain private and unchanged.',
     'All successful retained video header probes are included exactly once. Filename-redacted technical samples only; original media and audit records remain private and unchanged.'),
    (('methodology', 9),
     'A separate owner-confirmed 2CH front/telephoto time-lapse scan is retained under owner_scan. Its settings do not establish historical settings or cross-scan physical clip identity. Historical inside-to-telephoto attribution is separately owner-confirmed in channel_role_corrections. New numeric samples are deduplicated by numeric equality within channel/context; occurrence indices retain source order anonymously.',
     'A separate owner-confirmed 2CH front/telephoto time-lapse scan is retained under owner_scan. Its settings do not establish historical settings or cross-scan physical clip identity. Historical inside-to-telephoto attribution is separately owner-confirmed in channel_role_corrections. New numeric samples are deduplicated by numeric equality within channel/context; occurrence indices retain source order with filenames redacted.'),
    (('owner_scan', 'provenance'),
     'Separate owner-labeled stored scan; no private inventory identity match to the historical inspected card has been established.',
     'Separate Vortex Radar test-unit scan; cross-scan physical clip identity with the historical inspected card has not been established.'),
    (('source',), 'Vortex Radar, owner card inspection', 'Vortex Radar test unit, owner card inspection'),
]
PROFILE_CHANGES = [
    (('channel_variants', 1, 'variant'), 'New owner cohort only; historical physical identity not matched', 'Separate scan; cross-scan physical clip identity not matched'),
    (('evidence', 'confidence'), 'historical inside-to-telephoto owner-confirmed; separate new owner-confirmed front/telephoto time-lapse setup; other historical attribution and configured modes unconfirmed', 'All existing recordings: Vortex Radar test unit; configuration and settings remain batch-scoped'),
    (('notes', 0), 'All historical successful retained video header probes are included exactly once. The separate owner scan adds anonymous nested per-sample measurements; no physical clip identity or cross-scan uniqueness is inferred.', 'All historical successful retained video header probes are included exactly once. The separate owner scan adds filename-redacted nested per-sample measurements; no physical clip identity or cross-scan uniqueness is inferred.'),
    (('sources', 3, 'label'), 'Vortex Radar, owner card inspection; sanitized exact video evidence', 'Vortex Radar test unit; filename-redacted exact video evidence'),
    (('sources', 5, 'label'), 'Anonymous exact 72-clip 3CH driving/time-lapse measurements', 'Vortex Radar test unit; exact 72-clip 3CH driving/time-lapse measurements'),
]


def restore_leaves(value, changes):
    result = deepcopy(value)
    for path, old, new in changes:
        parent = result
        for key in path[:-1]:
            parent = parent[key]
        assert parent[path[-1]] == new, ('Unapproved attribution value', path)
        parent[path[-1]] = old
    return result


def prior_video_provenance(value):
    """Restore the exact pre-confirmation metadata; retain every other value."""
    result = restore_leaves(value, VIDEO_CHANGES)
    assert result.pop('recording_attribution') == ATTRIBUTION
    return result
