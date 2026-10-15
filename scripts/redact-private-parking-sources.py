#!/usr/bin/env python3
"""Remove private spreadsheet links while preserving contributed measurements."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_NOTES='https://vortexopenclaw.github.io/dashcam-camera-profiles/parking-mode.html#vortex-radar-testing'

def redact():
    path=ROOT/'parking/measurements.json'
    rows=json.loads(path.read_text())
    changed=0
    for row in rows:
        if row['tester']=='Vortex Radar' and ('docs.google.com/spreadsheets' in row['source_url'] or row.get('source_is_private')):
            changed+=not row.get('source_is_private',False)
            row['source_url']=PUBLIC_NOTES
            row['source_is_private']=True
    path.write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    path=ROOT/'parking/sources.json'
    sources=json.loads(path.read_text())
    for source in sources:
        if source['tester']=='Vortex Radar':
            source.update(url=PUBLIC_NOTES,title='Vortex Radar testing',private=True,notes='Measurements provided by Vortex Radar. The original spreadsheet is private.')
    path.write_text(json.dumps(sources,indent=2,ensure_ascii=False)+'\n')
    print(f'Redacted private links from {changed} contributed measurements. Measurement values were preserved.')

if __name__=='__main__':redact()
