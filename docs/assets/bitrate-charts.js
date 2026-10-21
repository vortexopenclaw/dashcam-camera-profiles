'use strict';
(async () => {
  const $ = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  const fmt = n => n.toFixed(1);
  const rate = row => fmt(row.lowMbps) === fmt(row.highMbps) ? fmt(row.highMbps) : `${fmt(row.lowMbps)} – ${fmt(row.highMbps)}`;
  const channels = row => `${row.channels}CH`;
  const codecKey = row => /265|hevc/i.test(row.codec) ? 'h265' : /264|avc/i.test(row.codec) ? 'h264' : null;
  const codecLabel = row => codecKey(row)==='h265' ? 'H.265' : 'H.264';
  const matchesCodec = row => $('codec').value==='all' || codecKey(row)===$('codec').value;
  const defaults = ['viofo-a329s','blackvue-elite-10','nextbase-622gw','viofo-t340','vueroid-s1-4k-infinite','viofo-a119m-pro','vantrue-e1-pro-s','viofo-a229-pro','vantrue-n4-pro-s','thinkware-arc-800','vantrue-e1-pro','thinkware-u3000-pro'];
  const measure = document.createElement('canvas').getContext('2d');
  const textWidth = (text, size=16, bold=false) => {
    measure.font=`${bold ? 700 : 400} ${size}px Arial, Helvetica, sans-serif`;
    return measure.measureText(text).width;
  };
  // Match parking charts, including safe wrapping of long unbroken custom text.
  const wrap = (text, width, size=16, bold=false) => {
    const lines=[];let line='';
    for (const char of String(text)) {
      if (line && textWidth(line+char,size,bold)>width) {
        const space=line.lastIndexOf(' ');
        if (space>line.length/2) {lines.push(line.slice(0,space));line=line.slice(space+1)+char;}
        else {lines.push(line);line=char;}
      } else line+=char;
    }
    if (line) lines.push(line);
    return lines;
  };
  const textControls={title:'4K30 Front-Camera Bitrate Comparison',subtitle:'Front Camera Bitrates at Maximum Quality',xLabel:'Video Bitrate (Mbps)',yLabel:'Dash Cameras'};
  try {
    const response = await fetch('data/bitrate-variants.json', {cache:'no-store'});
    if (!response.ok) throw new Error('Could not load camera measurements.');
    const rows = await response.json();
    if (!Array.isArray(rows)) throw new Error('Camera measurements are not a list.');
    for (const row of rows) {
      if (![row.lowMbps,row.highMbps].every(n=>typeof n==='number' && Number.isFinite(n) && n>=0) || row.highMbps<row.lowMbps) throw new Error(`Invalid bitrate measurement for ${row.camera || row.key}.`);
      if (!codecKey(row)) throw new Error(`Unverified video codec for ${row.camera || row.key}.`);
      if (!Number.isInteger(row.channels) || row.channels<1 || row.channels>4) throw new Error(`Invalid tested channel count for ${row.camera || row.key}.`);
    }
    const known = new Set(rows.map(r => r.key));
    const models = [...new Set(rows.map(r=>r.id))].map(id => {
      const variants=rows.filter(r=>r.id===id), preferred=variants.find(r=>r.default) || variants[0];
      return {id,camera:preferred.camera,variants,preferred};
    }).sort((a,b)=>a.camera.localeCompare(b.camera,undefined,{numeric:true}));
    const params = new URLSearchParams(location.search);
    let selected = new Set(params.has('selection') ? params.getAll('camera').filter(k => known.has(k)) : defaults.filter(k=>known.has(k)));
    $('format').value = params.get('format')==='auto' ? 'auto' : 'video';
    $('codec').value = ['h264','h265'].includes(params.get('codec')) ? params.get('codec') : 'all';
    $('sort').value = ['high','low','name'].includes(params.get('sort')) ? params.get('sort') : 'high';
    for (const [id,fallback] of Object.entries(textControls)) $(id).value=(params.get(id) ?? fallback).replace(/[\u0000-\u001f\u007f]/g,' ').slice(0,id.endsWith('Label') ? 120 : 180);
    for (const model of models) {
      const option=document.createElement('option');option.value=model.id;option.textContent=model.camera;$('highlight').append(option);
    }
    // IDs are canonical; accept model-name links too, as the parking builder does.
    const requested=params.get('highlight') || '';
    const highlighted=models.find(model=>model.id===requested || model.camera.toLowerCase()===requested.toLowerCase());
    $('highlight').value=highlighted?.id || '';
    let svgText = '';
    const ordered = (all=false) => rows.filter(r=>selected.has(r.key) && (all || matchesCodec(r))).sort((a,b)=>$('sort').value==='name' ? a.camera.localeCompare(b.camera,undefined,{numeric:true}) : ($('sort').value==='low' ? a.highMbps-b.highMbps : b.highMbps-a.highMbps));
    // The 16:9 export can have side gutters when many rows set its scale.
    // Start the narrow-screen scroller at the real content, not that blank gutter.
    function positionPreview() {
      const svg=$('chart').querySelector('svg');
      const content=svg?.querySelector(':scope > g');
      const gutter=content?.transform.baseVal.consolidate()?.matrix.e || 0;
      $('chart').scrollLeft=innerWidth<=760 && svg ? gutter*svg.clientWidth/Number(svg.getAttribute('width')) : 0;
    }
    window.addEventListener('resize',positionPreview);
    $('choices').replaceChildren();
    for (const model of models) {
      const card=document.createElement('div');card.className='camera-choice';card.dataset.search=model.camera.toLowerCase();card.dataset.model=model.id;
      const label=document.createElement('label');label.className='choice';
      const input=document.createElement('input');input.type='checkbox';input.value=model.id;input.dataset.model=model.id;
      input.addEventListener('change',()=>{
        const available=model.variants.filter(matchesCodec);
        if (input.checked) selected.add((available.find(row=>row.default) || available[0]).key);
        else for (const row of available) selected.delete(row.key);
        render();
      });
      const span=document.createElement('span');span.textContent=model.camera;
      const small=document.createElement('small');small.dataset.summary=model.id;span.append(small);label.append(input,span);card.append(label);
      if (model.variants.length>1 || model.preferred.unmeasuredSetups?.length) {
        const details=document.createElement('details');details.className='variant-options';
        const summary=document.createElement('summary');summary.textContent='Channel setups and units';details.append(summary);
        for (const row of model.variants) {
          const option=document.createElement('label');option.className='choice variant-choice';option.dataset.codec=codecKey(row);
          const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.value=row.key;checkbox.dataset.variant=row.key;
          checkbox.addEventListener('change',()=>{checkbox.checked ? selected.add(row.key) : selected.delete(row.key);render();});
          const text=document.createElement('span');
          const unit=row.key==='t340-a' ? 'Unit A' : row.key==='t340-b' ? 'Unit B' : row.key==='viofo-t340' ? 'Combined unit range' : row.variantLabel || channels(row);
          text.textContent=`${unit}${unit.includes(codecLabel(row)) ? '' : ' · '+codecLabel(row)} · ${rate(row)} Mbps`;
          if (row.variantLabel && !row.variantLabel.includes(channels(row))) text.textContent=`${channels(row)} · ${text.textContent}`;
          option.append(checkbox,text);details.append(option);
        }
        for (const setup of model.preferred.unmeasuredSetups || []) {const note=document.createElement('p');note.className='note';note.textContent=setup.note;details.append(note);}
        card.append(details);
      }
      $('choices').append(card);
    }
    function render() {
      for (const model of models) {
        const available=model.variants.filter(matchesCodec);
        const picked=available.filter(r=>selected.has(r.key)),preferred=available.find(r=>r.default) || available[0] || model.preferred;
        const card=[...$('choices').children].find(node=>node.dataset.model===model.id);
        card.hidden=!available.length || !card.dataset.search.includes($('search').value.toLowerCase());
        card.querySelector('input[data-model]').checked=!!picked.length;
        for (const option of card.querySelectorAll('.variant-choice')) option.hidden=$('codec').value!=='all' && option.dataset.codec!==$('codec').value;
        card.querySelector('[data-summary]').textContent=(picked.length>1 ? `${picked.length} configurations selected` : `${channels(picked[0] || preferred)} · ${codecLabel(picked[0] || preferred)} · ${rate(picked[0] || preferred)} Mbps`);
        for (const box of card.querySelectorAll('input[data-variant]')) box.checked=selected.has(box.value);
      }
      const picked=ordered();
      const automaticSubtitles=new Set([textControls.subtitle,'Front Camera Bitrates, Maximum Video Quality','Front Camera Bitrates at Selected Quality Settings']);
      if(automaticSubtitles.has($('subtitle').value)) $('subtitle').value=picked.some(row=>row.quality && row.quality!=='maximum') ? 'Front Camera Bitrates at Selected Quality Settings' : textControls.subtitle;
      const state=new URLSearchParams({selection:'1',sort:$('sort').value,format:$('format').value,highlight:$('highlight').value,codec:$('codec').value});
      for (const id of Object.keys(textControls)) state.set(id,$(id).value);
      for (const row of ordered(true)) state.append('camera',row.key);
      history.replaceState(null,'',`${location.pathname}?${state}`);
      $('png').disabled=$('svg').disabled=!picked.length;
      const hidden=selected.size-picked.length;
      $('status').textContent=(picked.length ? `${picked.length} camera results selected.` : selected.size ? 'No selected cameras match this codec.' : 'Choose a camera to draw your chart.')+(hidden ? ` ${hidden} selected results kept for other codecs.` : '');
      $('all').textContent=$('codec').value==='all' ? 'Compare all models' : 'Compare all '+$('codec').selectedOptions[0].textContent+' models';
      $('t340-note').hidden=!picked.some(row=>row.id==='viofo-t340');
      $('measurements').innerHTML=picked.map(row=>`<article><strong>${escape(row.camera)} · ${escape(channels(row))}</strong><br>${escape(codecLabel(row))} · ${escape(row.configuration)}${row.codecSource ? '<br>Codec evidence: '+escape(row.codecSource) : ''}<br>${escape(row.settings)}<br>Channel evidence: ${escape(row.channelSource || 'The tested channel count was not retained.')}<br>Source: ${escape(row.source)}<br>Video bitrate: ${rate(row)} Mbps</article>`).join('');
      if (!picked.length) {svgText='';$('chart').textContent=selected.size ? 'No selected cameras match this codec.' : 'No cameras selected.';return;}
      const video=$('format').value==='video';
      const labels=picked.map(row=>`${row.camera} · ${channels(row)} · ${codecLabel(row)}`);
      const left=Math.ceil(Math.min(330,Math.max(220,...labels.map(label=>textWidth(label,16,true)+64))));
      const right=Math.ceil(Math.max(110,...picked.map(row=>textWidth(`${rate(row)} Mbps`,16,true)))+35);
      const width=1200;
      const lines=labels.map(label=>wrap(label,left-56,16,true));
      const heights=lines.map(label=>Math.max(58,label.length*20+18));
      const parts=[];
      const text=(x,y,value,attrs='')=>parts.push(`<text x="${x}" y="${y}" ${attrs}>${escape(value)}</text>`);
      let y=45;
      for (const line of wrap($('title').value,width-72,28,true)) {
        text(width/2,y,line,'text-anchor="middle" data-role="chart-heading" font-size="28" font-weight="700" fill="#172337"');y+=35;
      }
      const subtitleLines=wrap($('subtitle').value,width-72,16);
      subtitleLines.forEach((line,i)=>text(width/2,y+8+i*22,line,'text-anchor="middle" data-role="chart-heading" font-size="16" fill="#516174"'));
      y+=Math.max(0,subtitleLines.length-1)*22;
      const top=y+50,bottom=top+heights.reduce((sum,h)=>sum+h,0);
      const maximum=Math.max(...picked.map(row=>row.highMbps));
      const rawStep=maximum>0 ? maximum/5 : .2,magnitude=10**Math.floor(Math.log10(rawStep));
      const step=[1,2,2.5,5,10].find(n=>n*magnitude>=rawStep)*magnitude;
      const max=Math.max(step,Math.ceil(maximum/step)*step);
      const x=n=>left+n/max*(width-left-right);
      for(let tick=0;tick<=Math.round(max/step);tick++) {
        const value=tick*step;
        parts.push(`<line x1="${x(value)}" x2="${x(value)}" y1="${top-12}" y2="${bottom}" stroke="${tick?'#e3e8ee':'#7e8996'}" stroke-width="${tick?1:1.5}"/>`);
        text(x(value),bottom+26,String(Number(value.toPrecision(3))),'text-anchor="middle" font-size="13" fill="#627084"');
      }
      let rowTop=top;
      picked.forEach((row,i)=>{
        const cy=rowTop+heights[i]/2,highlight=row.id===$('highlight').value;
        rowTop+=heights[i];
        parts.push(`<g data-variant="${escape(row.key)}" data-highlight="${highlight}">`);
        lines[i].forEach((line,j)=>text(left-20,cy-lines[i].length*10+15+j*20,line,`text-anchor="end" font-size="16" font-weight="${highlight?700:600}" fill="${highlight?'#ac520e':'#23354a'}"`));
        const color=highlight?'#ef8a2c':'#559bd4';
        if (row.highMbps>0) parts.push(`<rect data-kind="bar" x="${left}" y="${cy-13}" width="${x(row.highMbps)-left}" height="26" fill="${color}"/>`);
        else parts.push(`<circle cx="${left}" cy="${cy}" r="3" fill="${color}"/>`);
        if (row.highMbps>row.lowMbps) {
          parts.push(`<path data-kind="range" d="M${x(row.lowMbps)} ${cy}H${x(row.highMbps)}M${x(row.lowMbps)} ${cy-12}V${cy+12}M${x(row.highMbps)} ${cy-12}V${cy+12}" stroke="${highlight?'#ac520e':'#243a50'}" stroke-width="3" fill="none"/>`);
        }
        text(x(row.highMbps)+10,cy+5,`${rate(row)} Mbps`,`data-kind="value" font-size="16" font-weight="${highlight?700:600}" fill="#23354a"`);
        parts.push('</g>');
      });
      const axisLines=wrap($('xLabel').value,width-left-right,15);
      axisLines.forEach((line,i)=>text((left+width-right)/2,bottom+54+i*19,line,'text-anchor="middle" data-role="chart-axis" font-size="15" fill="#516174"'));
      const center=(top+bottom)/2;
      const yLines=wrap($('yLabel').value,bottom-top,15);
      yLines.forEach((line,i)=>text(24+i*18,center,line,`text-anchor="middle" data-role="chart-y-axis" font-size="15" fill="#516174" transform="rotate(-90 ${24+i*18} ${center})"`));
      y=bottom+80+Math.max(0,axisLines.length-1)*19;
      parts.push(`<line x1="36" x2="${width-36}" y1="${y-8}" y2="${y-8}" stroke="#dae2eb"/>`);
      if (picked.some(row=>row.highMbps>row.lowMbps)) {y+=19;text(36,y,'Bars show measured maxima. Markers show observed ranges.','font-size="13" fill="#536174"');y+=5;}
      y+=22;
      const contributors=[...new Set(picked.map(row=>/Retro CarGuy530|rcg530/.test(row.source) ? 'Retro CarGuy530 (rcg530)' : 'Vortex Radar'))].join(', ');
      for (const line of wrap(`Sources: ${contributors}. Full measurements and configurations: vortexopenclaw.github.io/dashcam-camera-profiles/4k30-comparison.html`,width-72,12)) {
        text(36,y,line,'font-size="12" fill="#69778a"');y+=17;
      }
      const height=y+30,outputWidth=video?1920:width,outputHeight=video?1080:height;
      const scale=video?Math.min(outputWidth/width,outputHeight/height):1;
      const transform=`translate(${(outputWidth-width*scale)/2} ${(outputHeight-height*scale)/2}) scale(${scale})`;
      svgText=`<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="bitrate-chart-title bitrate-chart-desc" viewBox="0 0 ${outputWidth} ${outputHeight}" width="${outputWidth}" height="${outputHeight}" font-family="Arial, Helvetica, sans-serif" font-size="14" fill="#263343"><title id="bitrate-chart-title">${escape($('title').value)}</title><desc id="bitrate-chart-desc">4K30 front-camera video bitrates. Ranges show endpoints, not averages. Audio excluded.</desc><metadata>${escape(JSON.stringify(picked))}</metadata><rect width="${outputWidth}" height="${outputHeight}" fill="#ffffff"/><g transform="${transform}">${parts.join('')}</g></svg>`;
      $('chart').innerHTML=svgText;
      positionPreview();
    }
    function download(blob,extension,layout=$('format').value,codec=$('codec').value) {
      const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`front-camera-bitrates-4k30${codec==='all'?'':'-'+codec}${layout==='video'?'-16x9':''}.${extension}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
    }
    $('search').addEventListener('input',render);
    $('all').onclick=()=>{selected=new Set([...rows.filter(row=>selected.has(row.key)&&!matchesCodec(row)).map(row=>row.key),...models.map(model=>{const available=model.variants.filter(matchesCodec);return (available.find(row=>row.default)||available[0])?.key;}).filter(Boolean)]);render();};
    $('clear').onclick=()=>{selected.clear();render();};
    $('defaults').onclick=()=>{$('codec').value='all';selected=new Set(defaults.filter(key=>known.has(key)));render();};
    $('format').onchange=render;
    $('sort').onchange=render;
    $('codec').onchange=render;
    $('highlight').onchange=render;
    for (const id of Object.keys(textControls)) $(id).addEventListener('input',render);
    $('svg').onclick=()=>download(new Blob([svgText],{type:'image/svg+xml'}),'svg');
    $('png').onclick=async()=>{
      const layout=$('format').value,codec=$('codec').value;
      const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'}));
      try {
        const image=new Image();image.src=url;await image.decode();
        const canvas=document.createElement('canvas');canvas.width=image.width*2;canvas.height=image.height*2;canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
        const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
        if (!blob) throw new Error('PNG export failed.');download(blob,'png',layout,codec);
      } catch(error) {$('status').textContent=error.message;} finally {URL.revokeObjectURL(url);}
    };
    $('share').onclick=async()=>{try {await navigator.clipboard.writeText(location.href);$('status').textContent='Chart link copied.';}catch {$('status').textContent='Copy the chart link from your address bar.';}};
    render();
  } catch(error) {$('choices').textContent='Camera measurements could not be loaded. Reload to try again.';$('status').textContent=error.message;}
})();
