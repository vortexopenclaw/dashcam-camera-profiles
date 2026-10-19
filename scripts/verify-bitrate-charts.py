#!/usr/bin/env python3
"""Exercise the real chart builder and downloads against local or live Pages."""
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

base = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8896/'
artifacts = Path.home() / '.hermes/cache/scratch/bitrate-chart-tests'
artifacts.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1400, 'height': 1000}, accept_downloads=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base + 'bitrate-charts.html')
    page.wait_for_selector('#chart svg')
    assert page.locator('#choices input:checked').count() == 2
    assert '41.0' in page.locator('#chart').inner_text()
    assert '53.3' in page.locator('#chart').inner_text()
    assert page.locator('#choices input[value="t340-a"]').is_checked()
    assert page.locator('#subtitle').input_value() == 'Front Camera Bitrates at Maximum Quality'
    assert 'not verified maximum-quality' not in page.locator('#chart').inner_text()
    custom_subtitle = 'Custom <subtitle> & quality'
    page.locator('#subtitle').fill(custom_subtitle)
    page.wait_for_function("document.querySelector('#chart').textContent.includes('Custom <subtitle> & quality')")
    e1s = page.locator('#choices input[value="vantrue-e1-pro-s"]')
    assert e1s.count() == 1
    e1s.check()
    assert '36.0' in page.locator('#chart').inner_text()
    assert 'Prototype' in page.locator('#chart').inner_text()
    e1s.uncheck()
    page.locator('#search').fill('A329S')
    assert page.locator('.choice:visible').count() == 1
    page.locator('input[value="viofo-a329s"]').check()
    assert page.locator('#choices input:checked').count() == 3
    page.locator('#sort').select_option('low')
    saved = page.url
    page.reload()
    page.wait_for_selector('#chart svg')
    assert page.locator('#choices input:checked').count() == 3
    assert page.locator('#sort').input_value() == 'low'
    assert page.locator('#subtitle').input_value() == custom_subtitle
    assert page.locator('#chart svg text tspan').first.text_content() == 'VIOFO T340 B • Maximum'
    for extension in ('svg', 'png'):
        with page.expect_download() as info:
            page.locator('#' + extension).click()
        target = artifacts / ('selected.' + extension)
        info.value.save_as(target)
        if extension == 'svg':
            root = ET.parse(target).getroot()
            assert custom_subtitle in ''.join(root.itertext())
            assert 'not verified maximum-quality' not in ''.join(root.itertext())
            records = json.loads(root.find('{http://www.w3.org/2000/svg}metadata').text)
            assert len(records) == 3
            t340 = {r['key']: r for r in records if r['id'] == 'viofo-t340'}
            assert t340['t340-a']['highMbps'] > t340['t340-b']['highMbps']
            assert all('firmware 1.0_260911' in r['configuration'] and 'bench and road tested' in r['configuration'] for r in t340.values())
            assert {r['key'] for r in records} == {'t340-a', 't340-b', 'viofo-a329s'}
        else:
            import struct
            raw = target.read_bytes()
            assert raw[:8] == b'\x89PNG\r\n\x1a\n'
            width, height = struct.unpack('>II', raw[16:24])
            assert width == 2240 and height > 0
    page.locator('#all').click()
    available = page.locator('#choices input').count()
    assert page.locator('#choices input:checked').count() == available
    assert '44.3 – 48.0' in page.locator('#chart').inner_text()
    assert '60.0' in page.locator('#chart').inner_text()
    assert '53.25' not in page.locator('#chart').inner_text()
    # All SVG text must remain inside the canvas, including the longest model name.
    assert page.evaluate('''() => [...document.querySelectorAll('#chart svg text')].every(t => {
      const b=t.getBBox(),s=document.querySelector('#chart svg').viewBox.baseVal;
      return b.x>=0 && b.x+b.width<=s.width && b.y>=0 && b.y+b.height<=s.height;
    })''')
    page.locator('#clear').click()
    assert page.locator('#chart svg').count() == 0 and page.locator('#png').is_disabled()
    page.reload()
    page.wait_for_function("document.querySelector('#status').textContent.includes('Choose a camera')")
    assert page.locator('#choices input:checked').count() == 0
    page.locator('#t340').click()
    assert page.locator('#choices input:checked').count() == 2
    for width in (390, 760, 1400):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
        page.screenshot(path=str(artifacts / f'width-{width}.png'), full_page=True)
    page.goto(base + 'bitrate-charts.html?selection=1&camera=__proto__&camera=t340-a&camera=t340-a&sort=evil')
    page.wait_for_selector('#chart svg')
    assert page.locator('#choices input:checked').count() == 1
    assert page.locator('#sort').input_value() == 'high'
    assert not errors, errors
    browser.close()
print(f'Passed: {available} selectable results, T340 defaults, selection/search, sort, shared reload, PNG/SVG downloads, label bounds, clear, mobile layout, and invalid URL state. Artifacts: {artifacts}')
