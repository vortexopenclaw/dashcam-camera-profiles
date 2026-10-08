#!/usr/bin/env python3
"""Render reviewed, privacy-safe T340 measurements; requires matplotlib."""
import csv
import html
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'docs/data/t340-quality-comparison.json').read_text())
OUT = ROOT / 'docs/assets/t340'
OUT.mkdir(parents=True, exist_ok=True)
ROWS = DATA['rows']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.axisbelow':True,'svg.fonttype':'none'})
COLORS = ['#277c9c','#277c9c','#277c9c','#277c9c','#399772','#399772']

def recorded_time(hours):
    minutes = round(hours * 60)
    whole_hours, remaining_minutes = divmod(minutes, 60)
    return f'{whole_hours} h {remaining_minutes:02d} min'

def finish(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=160, facecolor='white')
    fig.savefig(OUT / (name + '.svg'), facecolor='white')
    svg = OUT / (name + '.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    plt.close(fig)

def per_camera(front):
    rows = [*ROWS[:5], ROWS[6]]
    fig, axes = plt.subplots(1,2,figsize=(13,6.6))
    fig.subplots_adjust(left=.16,right=.96,top=.79,bottom=.23,wspace=.37)
    title = 'Front camera' if front else 'Add-on cameras: rear / interior / telephoto'
    fig.suptitle('VIOFO T340 • ' + title,fontsize=20,fontweight='bold',y=.95)
    fig.text(.5,.86,'4CH • 4K front / 2K add-ons • H.264, 30 fps',ha='center',fontsize=10,color='#536173')
    for axis, field, unit in zip(axes,['videoMbps','MBPerMinute'],['Encoded video bitrate (Mbps)','File consumption (MB/minute)']):
        vals=[]
        for row in rows:
            clips=[c for c in row['channels'] if (c['channel']=='front')==front]
            vals.append(clips[0][field])
        valid=[v for v in vals if v is not None]
        if front:
            axis.barh(range(len(rows)),[v or 0 for v in vals],color=COLORS,height=.63)
            for i,v in enumerate(vals):
                axis.text((v or 0)+max(valid)*.025,i,f'{v:.2f}' if v is not None else 'Full-minute sample pending',va='center',fontweight='bold',fontsize=10)
        else:
            for j,(role,color) in enumerate([('rear','#689cbe'),('interior','#88bda9'),('telephoto','#b3cf95')]):
                channel_vals=[next(c[field] for c in r['channels'] if c['channel']==role) for r in rows]
                axis.barh(np.arange(len(rows))+(j-1)*.21,[v or 0 for v in channel_vals],height=.19,color=color,label=role.title())
            for i,v in enumerate(vals):
                camera_vals=[c[field] for c in rows[i]['channels'] if c['channel']!='front' and c[field] is not None]
                label=(f'{min(camera_vals):.2f}–{max(camera_vals):.2f}' if field=='videoMbps' and f'{min(camera_vals):.2f}' != f'{max(camera_vals):.2f}' else f'{v:.2f} each') if v is not None else 'Full-minute sample pending'
                axis.text((max(camera_vals) if camera_vals else 0)+max(valid)*.025,i,label,va='center',fontsize=9)
        axis.set_yticks(range(len(rows)),['Auto Event Detection\nparking' if r['setting']=='Auto Event Detection parking' else r['setting'] for r in rows])
        axis.invert_yaxis();axis.set_xlim(0,max(valid)*1.42);axis.set_xlabel(unit);axis.grid(axis='x',alpha=.16)
        axis.set_title('Encoded video bitrate' if field=='videoMbps' else 'File size per recording minute',fontsize=14,fontweight='bold',pad=13)
    fig.text(.16,.125,'Firmware: '+DATA['firmware'],fontsize=10,color='#536173')
    if not front:
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, frameon=False, fontsize=9, ncol=3, loc='lower center', bbox_to_anchor=(.7,.115))
    fig.text(.16,.085,'Auto Event clips: 45 seconds, front 62.91 MB / each add-on 48.23 MB. Bars use file size × 60/45.',fontsize=10)
    fig.text(.16,.045,'Driving / Low Bitrate bars use one-minute files. Auto Event bars show MB per recorded minute.',fontsize=10)
    finish(fig,'front' if front else 'add-ons')

per_camera(True)
per_camera(False)
combined_rows = [*ROWS[:4], ROWS[5], ROWS[6], ROWS[4]]
fig,axis=plt.subplots(figsize=(13,8.3))
fig.subplots_adjust(left=.22,right=.74,top=.82,bottom=.23)
fig.suptitle('VIOFO T340 • Combined recording storage',fontsize=21,fontweight='bold',y=.95)
labels=[('Maximum (3CH)' if r['setting']=='Maximum 3CH' else 'Auto Event Detection\nparking (4CH)' if r['setting']=='Auto Event Detection parking' else r['setting']+' (4CH)') for r in combined_rows]
offset=np.zeros(len(combined_rows))
for role,color in [('front','#277c9c'),('rear','#689cbe'),('interior','#88bda9'),('telephoto','#b3cf95')]:
    values=[sum(c['MBPerMinute'] or 0 for c in r['channels'] if c['channel']==role) for r in combined_rows]
    bars=axis.barh(range(len(combined_rows)),values,left=offset,color=color,label=role.title(),height=.6)
    offset+=values
axis.set_yticks(range(len(combined_rows)),labels);axis.invert_yaxis();axis.set_xlim(0,1100);axis.set_xlabel('Combined MB per active recording minute');axis.grid(axis='x',alpha=.16)
for i,row in enumerate(combined_rows):
    if row['combinedMBPerMinute'] is None:
        axis.text(15,i,'Normal full-minute files: pending',va='center',fontsize=10)
        continue
    axis.text(row['combinedMBPerMinute']+15,i,f"{row['combinedMBPerMinute']:,.1f}",va='center',fontsize=10)
    capacity=recorded_time(row['nominal256GBRecordedHours'])
    axis.text(1.09,i,f"{row['combinedGBPerHour']:.2f} GB/h     {capacity}",transform=axis.get_yaxis_transform(),va='center',fontsize=11,fontweight='bold')
axis.text(1.09,1.045,'Storage rate     256 GB capacity',transform=axis.transAxes,fontsize=10)
fig.legend(loc='lower left',bbox_to_anchor=(.22,.82),ncol=4,frameon=False,fontsize=10)
fig.text(.22,.125,'256 GB capacity = nominal capacity / rate. No formatting, reserved space or protected-file allowance.',fontsize=10)
fig.text(.22,.085,'Capacity is hours of recorded footage across all connected cameras, not elapsed parked time.',fontsize=10)
fig.text(.22,.045,'Firmware: '+DATA['firmware']+' • Auto Event Detection: 45-second files converted to MB/minute.',fontsize=10)
finish(fig,'combined')

fig,axes=plt.subplots(1,2,figsize=(13,6.6))
fig.subplots_adjust(left=.14,right=.96,top=.79,bottom=.26,wspace=.4)
fig.suptitle('VIOFO T340 • Parking modes while recording',fontsize=20,fontweight='bold',y=.95)
fig.text(.5,.87,f"256 GB • 4CH footage: Low Bitrate {recorded_time(ROWS[4]['nominal256GBRecordedHours'])} / Auto Event Detection {recorded_time(ROWS[6]['nominal256GBRecordedHours'])}",ha='center',fontsize=12)
for axis,field,unit in zip(axes,['videoMbps','MBPerMinute'],['Encoded video bitrate (Mbps)','Whole file size (MB/min)']):
    for i,(role,label,color) in enumerate([('front','Front','#277c9c'),('rear','Rear / interior / telephoto','#399772')]):
        vals=[next(c[field] for c in r['channels'] if c['channel']==role) for r in [ROWS[4],ROWS[6]]]
        axis.bar(np.arange(2)+(i-.5)*.27,vals,width=.27,label=label,color=color)
        for j,v in enumerate(vals):axis.text(j+(i-.5)*.27,v+.3 if field=='videoMbps' else v+2,f'{v:.2f}',ha='center',fontsize=11)
    axis.set_xticks([0,1],['Low Bitrate','Auto Event Detection']);axis.set_ylabel(unit);axis.grid(axis='y',alpha=.16);axis.set_ylim(0,14 if field=='videoMbps' else 100);axis.legend(frameon=False,fontsize=9)
    axis.set_title('Encoded video bitrate' if field=='videoMbps' else 'File consumption while recording',fontsize=14,fontweight='bold',pad=13)
fig.text(.14,.15,'Auto Event Detection clips are 45 seconds long: front 62.91 MB / add-ons 48.23 MB each.',fontsize=10)
fig.text(.14,.105,'Whole-file sizes are extrapolated to MB/minute: 45-second file size × 60/45.',fontsize=10)
fig.text(.14,.065,'Capacity is recorded footage, not elapsed parked time. Formatting and other files reduce capacity.',fontsize=10)
fig.text(.14,.025,'Firmware: '+DATA['firmware']+' • Auto Event scan: Maximum driving bitrate selected.',fontsize=10)
finish(fig,'parking')

fields=['setting','channelCount','channel','videoMbps','MBPerMinute','basis','clipSizeBytes','clipDurationSeconds','combinedGBPerHour','nominal256GBRecordedHours']
with (OUT/'measurements.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for r in ROWS:
        for c in r['channels']:
            writer.writerow({k:(c.get(k) if k in c else r.get(k)) for k in fields})

images=''.join(f'<section><h2>{title}</h2><a href="assets/t340/{name}.png"><img src="assets/t340/{name}.png" alt="{title}" loading="lazy"></a><p><a href="assets/t340/{name}.svg">SVG</a> · <a href="assets/t340/{name}.png">PNG</a></p></section>' for name,title in [('front','Front camera'),('add-ons','Rear, interior and telephoto'),('combined','Combined storage and capacity'),('parking','Parking mode comparison')])
def display(value):
    return f'{value:.2f}' if value is not None else 'Pending'
table=''.join('<tr>'+''.join(f'<td>{v}</td>' for v in [html.escape(r['setting']),r['channelCount'],display(r['combinedMBPerMinute']),display(r['combinedGBPerHour']),recorded_time(r['nominal256GBRecordedHours']),'Measured files'])+'</tr>' for r in combined_rows)
notes=''.join('<li>'+html.escape(n)+'</li>' for n in DATA['limitations'])
page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>T340 bitrate and storage charts</title><style>body{font:16px system-ui;margin:32px auto;max-width:1100px;padding:0 18px;color:#182733;line-height:1.6}img{width:100%;height:auto}section{margin:32px 0}a{color:#146c93}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd}.scroll{overflow:auto}</style><a href="./">Camera reference</a><h1>VIOFO T340: bitrate, file size and recording capacity</h1><p>Measured metadata reviewed 2026-10-08. Four-channel driving, three-channel Maximum, and distinct parking settings.</p><p><strong>Firmware: '+html.escape(DATA['firmware'])+'.</strong> Bitrate panels measure encoded video; file panels measure whole files. Rear, interior and telephoto are shown separately: their sampled driving rates differ by less than 0.01 Mbps and their measured full-minute file sizes match.</p><p>Normal: 243.27 MB per minute front and 111.15 MB per minute for each add-on. All storage bars use measured files, with no video-only estimates.</p>'+images+'<h2>Combined measurements</h2><div class="scroll"><table><tr><th>Setting</th><th>Cameras</th><th>MB/min</th><th>GB/hour</th><th>256 GB recorded time</th><th>Storage evidence</th></tr>'+table+'</table></div><h2>Measurement notes</h2><p>'+html.escape(DATA['method'])+'</p><ul>'+notes+'</ul><p><a href="assets/t340/measurements.csv">Download CSV</a> · <a href="data/t340-quality-comparison.json">Reviewed data JSON</a> · <a href="https://github.com/vortexopenclaw/dashcam-offloader/blob/main/docs/card-profiles/viofo-t340.md">Evidence notes</a></p></html>'
(ROOT/'docs/t340-comparison.html').write_text(page+'\n')
print('Rendered four PNG/SVG charts, CSV and report page')
