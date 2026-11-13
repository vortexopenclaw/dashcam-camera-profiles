#!/usr/bin/env python3
"""Validate scoped DDPAI model-reference identities without capability claims."""
import collections
import json
from pathlib import Path
from urllib.parse import urlsplit

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'docs/data/ddpai-model-reference.json').read_text())
assert data['schemaVersion']==1 and data['manufacturer']=='DDPAI'
rows=data['records']; assert len({r['id'] for r in rows})==len(rows)
assert len(rows)==data['counts']['identityRows']
regions=collections.Counter(r['region'] for r in rows)
assert regions['global-English']==data['counts']['globalEnglishRows']
assert regions['China']==data['counts']['chinaRegionalRows']
for row in rows:
    assert isinstance(row['model'],str) and row['model']
    assert isinstance(row['recognitionEligible'],bool)
    assert row['sources'] and isinstance(row['aliases'],list)
    if 'mismatch' in row['status']: assert not row['recognitionEligible']
    for url in row['sources']:
        parsed=urlsplit(url)
        assert parsed.scheme=='https' and parsed.hostname in {'ddpai.com','www.ddpai.com','cn.ddpai.com','store.ddpai.com'}
    for forbidden in ['channelCount','maxChannels','firmwareVersion','rawLog','filename','logSkuAliases']:
        assert forbidden not in row
text=json.dumps(data)
for forbidden in ['wifi_pwd','sn_code','bt_info','soft_version','DZ2602_GLOBAL']:
    assert forbidden not in text
print(f"DDPAI reference passed: {len(rows)} scoped identity rows; {dict(regions)}; no hardware/channel/log-SKU equivalence asserted")
