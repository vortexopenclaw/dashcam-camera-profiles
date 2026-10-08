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
COLORS = ['#277c9c','#eda34b','#277c9c','#277c9c','#399772']

def finish(fig, name):
    fig.savefig(OUT / (name + '.png'), dpi=160, facecolor='white')
    fig.savefig(OUT / (name + '.svg'), facecolor='white')
    plt.close(fig)

def per_camera(front):
    fig, axes = plt.subplots(1,2,figsize=(13,6.6))
    fig.subplots_adjust(left=.16,right=.96,top=.79,bottom=.23,wspace=.37)
    title = 'Front camera' if front else 'Add-on cameras: rear / interior / telephoto'
    fig.suptitle('VIOFO T340 • ' + title,fontsize=20,fontweight='bold',y=.95)
    fig.text(.16,.86,'4CH • representative samples • 4K front / 1440p add-ons • H.264, 30 fps',fontsize=11,color='#536173')
    for axis, field, unit in zip(axes,['videoMbps','MBPerMinute'],['Encoded video bitrate (Mbps)','File consumption (MB/minute)']):
        vals=[]
        for row in ROWS[:5]:
            clips=[c for c in row['channels'] if (c['channel']=='front')==front]
            vals.append(sum(c[field] for c in clips)/len(clips))
        bars=axis.barh(range(5),vals,color=COLORS,height=.63)
        if field == 'MBPerMinute':
            bars[1].set_hatch('///')
        for i,v in enumerate(vals):axis.text(v+max(vals)*.025,i,f'{v:.2f}',va='center',fontweight='bold')
        axis.set_yticks(range(5),[r['setting'] for r in ROWS[:5]])
        axis.invert_yaxis();axis.set_xlim(0,max(vals)*1.22);axis.set_xlabel(unit);axis.grid(axis='x',alpha=.16)
    fig.text(.16,.125,'Orange hatched Normal file bar = VIDEO-ONLY ESTIMATE; actual file size is not paired with duration.',fontsize=10,color='#9a5a14')
    fig.text(.16,.085,'Other file bars use measured 60-second clips. MB is decimal; 1 MB = 1,000,000 bytes.',fontsize=10)
    fig.text(.16,.045,'Maximum uses selected full-minute Maximum-sized clips from a mixed-rate card. Add-on bitrates are averaged.',fontsize=10)
    finish(fig,'front' if front else 'add-ons')

per_camera(True)
per_camera(False)
fig,axis=plt.subplots(figsize=(13,8.3))
fig.subplots_adjust(left=.22,right=.74,top=.82,bottom=.23)
fig.suptitle('VIOFO T340 • Combined recording storage',fontsize=21,fontweight='bold',y=.95)
fig.text(.22,.87,'Whole-file rates except Normal estimate • Parking rows show active recording only',fontsize=11)
labels=[('Maximum (3CH)' if r['setting']=='Maximum 3CH' else r['setting']+' (4CH)') for r in ROWS]
offset=np.zeros(len(ROWS))
for role,color in [('front','#277c9c'),('rear','#689cbe'),('interior','#88bda9'),('telephoto','#b3cf95')]:
    values=[sum(c['MBPerMinute'] for c in r['channels'] if c['channel']==role) for r in ROWS]
    bars=axis.barh(range(len(ROWS)),values,left=offset,color=color,label=role.title(),height=.6)
    bars[1].set_hatch('///');offset+=values
axis.set_yticks(range(len(ROWS)),labels);axis.invert_yaxis();axis.set_xlim(0,1100);axis.set_xlabel('Combined MB per active recording minute');axis.grid(axis='x',alpha=.16)
for i,row in enumerate(ROWS):
    axis.text(row['combinedMBPerMinute']+15,i,f"{row['combinedMBPerMinute']:,.1f}",va='center',fontsize=10)
    axis.text(1.09,i,f"{row['combinedGBPerHour']:.2f} GB/h     {row['nominal256GBRecordedHours']:.2f} h",transform=axis.get_yaxis_transform(),va='center',fontsize=11,fontweight='bold')
axis.text(1.09,1.045,'Storage rate     256 GB capacity',transform=axis.transAxes,fontsize=10)
fig.legend(loc='lower left',bbox_to_anchor=(.22,.82),ncol=4,frameon=False,fontsize=10)
fig.text(.22,.125,'256 GB hours = nominal capacity / rate. No formatting, reserved space or protected-file allowance.',fontsize=10)
fig.text(.22,.085,'Parking capacity is recorded-footage hours, NOT elapsed parked time. Auto Event duty cycle is unknown.',fontsize=10)
fig.text(.22,.045,'Normal is video-only (hatched). Auto Event uses typical 45-second paired clips normalized to one minute.',fontsize=10)
finish(fig,'combined')

fig,axes=plt.subplots(1,2,figsize=(13,6.6))
fig.subplots_adjust(left=.14,right=.96,top=.79,bottom=.26,wspace=.4)
fig.suptitle('VIOFO T340 • Parking modes while recording',fontsize=20,fontweight='bold',y=.95)
for axis,field,unit in zip(axes,['videoMbps','MBPerMinute'],['Encoded video bitrate (Mbps)','Whole-file MB per active minute']):
    for i,(role,label,color) in enumerate([('front','Front','#277c9c'),('rear','Add-on typical','#399772')]):
        vals=[next(c[field] for c in r['channels'] if c['channel']==role) for r in [ROWS[4],ROWS[6]]]
        axis.bar(np.arange(2)+(i-.5)*.27,vals,width=.27,label=label,color=color)
        for j,v in enumerate(vals):axis.text(j+(i-.5)*.27,v+.3 if field=='videoMbps' else v+2,f'{v:.2f}',ha='center',fontsize=11)
    axis.set_xticks([0,1],['Low Bitrate','Auto Event typical']);axis.set_ylabel(unit);axis.grid(axis='y',alpha=.16);axis.set_ylim(0,14 if field=='videoMbps' else 100);axis.legend(frameon=False,fontsize=10)
fig.text(.14,.15,'Typical Auto Event files: front 62.91 MB / 45 sec; each add-on 48.23 MB / 45 sec.',fontsize=11)
fig.text(.14,.105,'Variation: one telephoto clip = 6.01 Mbps, 35.65 MB / 45 sec (47.54 MB/min), below the typical rate.',fontsize=10)
fig.text(.14,.065,'Impact-labelled groups contain mixed rates/durations; these bars are NOT an impact-event average.',fontsize=10)
fig.text(.14,.025,'Active recording consumption does not determine elapsed parked retention without event duty-cycle data.',fontsize=10)
finish(fig,'parking')

fields=['setting','channelCount','channel','videoMbps','MBPerMinute','basis','clipSizeBytes','clipDurationSeconds','combinedGBPerHour','nominal256GBRecordedHours']
with (OUT/'measurements.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
    for r in ROWS:
        for c in r['channels']:
            writer.writerow({k:(c.get(k) if k in c else r.get(k)) for k in fields})

images=''.join(f'<section><h2>{title}</h2><a href="assets/t340/{name}.png"><img src="assets/t340/{name}.png" alt="{title}" loading="lazy"></a><p><a href="assets/t340/{name}.svg">SVG</a> · <a href="assets/t340/{name}.png">PNG</a></p></section>' for name,title in [('front','Front camera'),('add-ons','Rear, interior and telephoto'),('combined','Combined storage and capacity'),('parking','Parking mode comparison')])
table=''.join('<tr>'+''.join(f'<td>{v}</td>' for v in [html.escape(r['setting']),r['channelCount'],f"{r['combinedMBPerMinute']:.2f}",f"{r['combinedGBPerHour']:.2f}",f"{r['nominal256GBRecordedHours']:.2f}",'Video-only estimate' if r['setting']=='Normal' else 'Paired files'])+'</tr>' for r in ROWS)
notes=''.join('<li>'+html.escape(n)+'</li>' for n in DATA['limitations'])
page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>T340 bitrate and storage charts</title><style>body{font:16px system-ui;margin:32px auto;max-width:1100px;padding:0 18px;color:#182733;line-height:1.6}img{width:100%;height:auto}section{margin:32px 0}a{color:#146c93}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd}.scroll{overflow:auto}</style><a href="./">Camera reference</a><h1>VIOFO T340: bitrate, file size and recording capacity</h1><p>Measured app-submission metadata reviewed 2026-10-08. Four-channel driving comparisons, separately confirmed three-channel Maximum, and distinct parking settings.</p><p><strong>Normal storage is a video-only estimate.</strong> Other main driving/file bars use paired full-minute clips. Maximum is a representative selected configuration from a mixed-rate card. MB and GB are decimal.</p>'+images+'<h2>Combined measurements</h2><div class="scroll"><table><tr><th>Setting</th><th>Cameras</th><th>MB/min</th><th>GB/hour</th><th>256 GB recorded hours</th><th>Storage evidence</th></tr>'+table+'</table></div><h2>Method and limitations</h2><p>'+html.escape(DATA['method'])+'</p><ul>'+notes+'</ul><p><a href="assets/t340/measurements.csv">Download CSV</a> · <a href="data/t340-quality-comparison.json">Reviewed data JSON</a> · <a href="https://github.com/vortexopenclaw/dashcam-offloader/blob/main/docs/card-profiles/viofo-t340.md">Evidence notes</a></p></html>'
(ROOT/'docs/t340-comparison.html').write_text(page+'\n')
print('Rendered four PNG/SVG charts, CSV and report page')
