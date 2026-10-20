'use strict';
(async () => {
  const $ = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  const fmt = n => n.toFixed(1);
  const rate = row => fmt(row.lowMbps) === fmt(row.highMbps) ? fmt(row.highMbps) : `${fmt(row.lowMbps)} – ${fmt(row.highMbps)}`;
  const channels = row => row.channels ? `${row.channels}CH` : 'CH unrecorded';
  const defaults = ['viofo-a329s','blackvue-elite-10','nextbase-622gw','viofo-t340','vueroid-s1-4k-infinite','viofo-a119m-pro','vantrue-e1-pro-s','viofo-a229-pro','vantrue-n4-pro-s','thinkware-arc-800','vantrue-e1-pro','thinkware-u3000-pro'];
  const wrap = (text, length=32) => {
    const lines=[''];
    for (const word of text.split(' ')) {
      if ((lines[lines.length-1]+' '+word).trim().length>length) lines.push(word);
      else lines[lines.length-1]=(lines[lines.length-1]+' '+word).trim();
    }
    return lines;
  };
  try {
    const response = await fetch('data/bitrate-variants.json', {cache:'no-store'});
    if (!response.ok) throw new Error('Could not load camera measurements.');
    const rows = await response.json();
    const known = new Set(rows.map(r => r.key));
    const models = [...new Set(rows.map(r=>r.id))].map(id => {
      const variants=rows.filter(r=>r.id===id), preferred=variants.find(r=>r.default) || variants[0];
      return {id,camera:preferred.camera,variants,preferred};
    }).sort((a,b)=>a.camera.localeCompare(b.camera,undefined,{numeric:true}));
    const params = new URLSearchParams(location.search);
    let selected = new Set(params.has('selection') ? params.getAll('camera').filter(k => known.has(k)) : defaults.filter(k=>known.has(k)));
    $('format').value = params.get('format')==='auto' ? 'auto' : 'video';
    $('sort').value = ['high','low','name'].includes(params.get('sort')) ? params.get('sort') : 'high';
    $('subtitle').value = (params.get('subtitle') ?? 'Front Camera Bitrates at Maximum Quality').slice(0,100);
    let svgText = '';
    const ordered = () => rows.filter(r=>selected.has(r.key)).sort((a,b)=>$('sort').value==='name' ? a.camera.localeCompare(b.camera,undefined,{numeric:true}) : ($('sort').value==='low' ? a.highMbps-b.highMbps : b.highMbps-a.highMbps));
    $('choices').replaceChildren();
    for (const model of models) {
      const card=document.createElement('div');card.className='camera-choice';card.dataset.search=model.camera.toLowerCase();card.dataset.model=model.id;
      const label=document.createElement('label');label.className='choice';
      const input=document.createElement('input');input.type='checkbox';input.value=model.id;input.dataset.model=model.id;
      input.addEventListener('change',()=>{
        if (input.checked) selected.add(model.preferred.key);
        else for (const row of model.variants) selected.delete(row.key);
        render();
      });
      const span=document.createElement('span');span.textContent=model.camera;
      const small=document.createElement('small');small.dataset.summary=model.id;span.append(small);label.append(input,span);card.append(label);
      if (model.variants.length>1 || model.preferred.unmeasuredSetups?.length) {
        const details=document.createElement('details');details.className='variant-options';
        const summary=document.createElement('summary');summary.textContent='Channel setups and units';details.append(summary);
        for (const row of model.variants) {
          const option=document.createElement('label');option.className='choice variant-choice';
          const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.value=row.key;checkbox.dataset.variant=row.key;
          checkbox.addEventListener('change',()=>{checkbox.checked ? selected.add(row.key) : selected.delete(row.key);render();});
          const text=document.createElement('span');
          const unit=row.key==='t340-a' ? 'Unit A' : row.key==='t340-b' ? 'Unit B' : row.key==='viofo-t340' ? 'Combined unit range' : row.variantLabel || channels(row);
          text.textContent=`${unit} · ${rate(row)} Mbps`;
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
        const picked=model.variants.filter(r=>selected.has(r.key));
        const card=[...$('choices').children].find(node=>node.dataset.model===model.id);
        card.querySelector('input[data-model]').checked=!!picked.length;
        card.querySelector('[data-summary]').textContent=(picked.length>1 ? `${picked.length} configurations selected` : `${channels(picked[0] || model.preferred)} · ${rate(picked[0] || model.preferred)} Mbps`);
        for (const box of card.querySelectorAll('input[data-variant]')) box.checked=selected.has(box.value);
      }
      const picked=ordered();
      const state=new URLSearchParams({selection:'1',sort:$('sort').value,subtitle:$('subtitle').value,format:$('format').value});
      for (const row of picked) state.append('camera',row.key);
      history.replaceState(null,'',`${location.pathname}?${state}`);
      $('png').disabled=$('svg').disabled=!picked.length;
      $('status').textContent=picked.length ? `${picked.length} camera results selected.` : 'Choose a camera to draw your chart.';
      $('t340-note').hidden=!picked.some(row=>row.id==='viofo-t340');
      $('measurements').innerHTML=picked.map(row=>`<article><strong>${escape(row.camera)} · ${escape(channels(row))}</strong><br>${escape(row.codec)} · ${escape(row.configuration)}<br>${escape(row.settings)}<br>Channel evidence: ${escape(row.channelSource || 'The tested channel count was not retained.')}<br>Source: ${escape(row.source)}<br>Video bitrate: ${rate(row)} Mbps</article>`).join('');
      if (!picked.length) {svgText='';$('chart').textContent='No cameras selected.';return;}
      const video=$('format').value==='video';
      const width=video?1600:1120,left=video?430:360,right=video?190:160,top=video?126:112,bottom=124;
      const font=video?22:18,lineHeight=video?24:20,barHeight=video?36:28;
      const labels=picked.map(row=>wrap(`${row.camera} · ${channels(row)}`,video?34:32));
      const minimum=labels.map(lines=>Math.max(video?56:48,lines.length*lineHeight+16));
      const extra=video?Math.max(0,900-top-bottom-minimum.reduce((a,b)=>a+b,0))/picked.length:0;
      const heights=minimum.map(h=>h+extra);
      const height=top+heights.reduce((a,b)=>a+b,0)+bottom;
      const outputWidth=video?1920:width,outputHeight=video?1080:height;
      const scale=video?Math.min(outputWidth/width,outputHeight/height):1;
      const transform=`translate(${(outputWidth-width*scale)/2} ${(outputHeight-height*scale)/2}) scale(${scale})`;
      const max=Math.ceil(Math.max(...picked.map(row=>row.highMbps))/10)*10;
      const x=n=>left+n/max*(width-left-right);
      const parts=[`<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Selected 4K30 front-camera video bitrates" viewBox="0 0 ${outputWidth} ${outputHeight}" width="${outputWidth}" height="${outputHeight}"><rect width="${outputWidth}" height="${outputHeight}" fill="white"/><g transform="${transform}" font-family="Arial, sans-serif" fill="#182733"><text x="${width/2}" y="${video?44:34}" font-size="${video?36:26}" font-weight="700" text-anchor="middle">4K30 Front-Camera Bitrate Comparison</text><text x="${width/2}" y="${video?84:65}" font-size="${video?24:17}" text-anchor="middle">${escape($('subtitle').value)}</text>`];
      for(let tick=0;tick<=max;tick+=10) parts.push(`<path d="M${x(tick)} ${top-16}V${height-bottom+4}" stroke="#e0e5eb"/><text x="${x(tick)}" y="${height-bottom+30}" text-anchor="middle" font-size="${video?20:16}">${tick}</text>`);
      let rowTop=top;
      picked.forEach((row,i)=>{
        const y=rowTop+heights[i]/2,highlight=row.id==='viofo-t340',lines=labels[i];rowTop+=heights[i];
        const label=lines.map((line,j)=>`<tspan x="${left-18}" dy="${j?lineHeight:0}">${escape(line)}</tspan>`).join('');
        parts.push(`<g data-variant="${escape(row.key)}"><text x="${left-18}" y="${y+font/3-(lines.length-1)*lineHeight/2}" text-anchor="end" font-size="${font}" font-weight="${highlight?'700':'400'}">${label}</text><rect x="${left}" y="${y-barHeight/2}" width="${x(row.highMbps)-left}" height="${barHeight}" fill="${highlight?'#ee8a19':'#23839d'}"/>`);
        if (row.highMbps>row.lowMbps) parts.push(`<path d="M${x(row.lowMbps)} ${y}H${x(row.highMbps)}M${x(row.lowMbps)} ${y-8}V${y+8}M${x(row.highMbps)} ${y-8}V${y+8}" stroke="#182733" stroke-width="2"/>`);
        parts.push(`<text x="${x(row.highMbps)+10}" y="${y+font/3}" font-size="${font}" font-weight="700">${rate(row)}</text></g>`);
      });
      parts.push(`<text x="${(left+width-right)/2}" y="${height-bottom+60}" text-anchor="middle" font-size="${font}">Video Bitrate (Mbps)</text><text x="28" y="${height-36}" font-size="15">Vortex Radar testing library · Video bitrate only, audio excluded.</text><text x="28" y="${height-12}" font-size="15">Channel setups are shown where recorded. Codecs and setups differ.</text></g><metadata>${escape(JSON.stringify(picked))}</metadata></svg>`);
      svgText=parts.join('');$('chart').innerHTML=svgText;
    }
    function download(blob,extension,layout=$('format').value) {
      const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`front-camera-bitrates-4k30${layout==='video'?'-16x9':''}.${extension}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
    }
    $('search').addEventListener('input',()=>{for (const card of $('choices').children) card.hidden=!card.dataset.search.includes($('search').value.toLowerCase());});
    $('all').onclick=()=>{selected=new Set(models.map(model=>model.preferred.key));render();};
    $('clear').onclick=()=>{selected.clear();render();};
    $('defaults').onclick=()=>{selected=new Set(defaults.filter(key=>known.has(key)));render();};
    $('t340').onclick=()=>{selected=new Set(['viofo-t340']);render();};
    $('format').onchange=render;
    $('sort').onchange=render;$('subtitle').addEventListener('input',render);
    $('svg').onclick=()=>download(new Blob([svgText],{type:'image/svg+xml'}),'svg');
    $('png').onclick=async()=>{
      const layout=$('format').value;
      const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'}));
      try {
        const image=new Image();image.src=url;await image.decode();
        const canvas=document.createElement('canvas');canvas.width=image.width*2;canvas.height=image.height*2;canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
        const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
        if (!blob) throw new Error('PNG export failed.');download(blob,'png',layout);
      } catch(error) {$('status').textContent=error.message;} finally {URL.revokeObjectURL(url);}
    };
    $('share').onclick=async()=>{try {await navigator.clipboard.writeText(location.href);$('status').textContent='Chart link copied.';}catch {$('status').textContent='Copy the chart link from your address bar.';}};
    render();
  } catch(error) {$('choices').textContent='Camera measurements could not be loaded. Reload to try again.';$('status').textContent=error.message;}
})();
