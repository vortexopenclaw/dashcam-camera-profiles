'use strict';
(async () => {
  const $ = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  const clean = value => value.replace(/\\u([0-9a-f]{4})/gi, (_, n) => String.fromCharCode(parseInt(n, 16)));
  const fmt = n => n.toFixed(1);
  try {
    const response = await fetch('data/4k30-comparison.json', {cache:'no-store'});
    if (!response.ok) throw new Error('Could not load camera measurements.');
    const data = await response.json();
    // Keep the two verified Maximum T340 units, not the historical lower presets.
    const rows = data.filter(r => r.id !== 'viofo-t340' || /Maximum/.test(r.camera)).map(r => ({...r, camera:clean(r.camera).replace(/\s*•\s*Maximum$/, ''), configuration:clean(r.configuration), key:r.id === 'viofo-t340' ? (/T340 A/.test(r.camera) ? 't340-a' : 't340-b') : r.id}));
    const known = new Set(rows.map(r => r.key));
    const params = new URLSearchParams(location.search);
    let selected = new Set(params.has('selection') ? params.getAll('camera').filter(k => known.has(k)) : ['t340-a','t340-b']);
    $('sort').value = ['high','low','name'].includes(params.get('sort')) ? params.get('sort') : 'high';
    $('subtitle').value = (params.get('subtitle') ?? 'Front Camera Bitrates at Maximum Quality').slice(0,100);
    let svgText = '';
    const ordered = () => rows.filter(r => selected.has(r.key)).sort((a,b) => $('sort').value === 'name' ? a.camera.localeCompare(b.camera, undefined, {numeric:true}) : ($('sort').value === 'low' ? a.highMbps-b.highMbps : b.highMbps-a.highMbps));
    const list = [...rows].sort((a,b) => a.camera.localeCompare(b.camera, undefined, {numeric:true}));
    for (const r of list) {
      const label = document.createElement('label');
      label.className = 'choice';
      label.dataset.search = r.camera.toLowerCase();
      const input = document.createElement('input');
      input.type = 'checkbox'; input.value = r.key; input.checked = selected.has(r.key);
      input.addEventListener('change', () => {input.checked ? selected.add(r.key) : selected.delete(r.key); render();});
      const span = document.createElement('span');
      span.textContent = r.camera;
      const small = document.createElement('small');
      small.textContent = `${fmt(r.highMbps)} Mbps`;
      span.append(small); label.append(input,span); $('choices').append(label);
    }
    // Remove only the initial loading text, retaining all checkbox nodes.
    for (const node of [...$('choices').childNodes]) if (node.nodeType === Node.TEXT_NODE) node.remove();
    function render() {
      for (const input of $('choices').querySelectorAll('input')) input.checked = selected.has(input.value);
      const picked = ordered();
      const state = new URLSearchParams({selection:'1',sort:$('sort').value,subtitle:$('subtitle').value});
      for (const r of picked) state.append('camera',r.key);
      history.replaceState(null,'',`${location.pathname}?${state}`);
      $('png').disabled = $('svg').disabled = !picked.length;
      $('status').textContent = picked.length ? `${picked.length} camera results selected.` : 'Choose a camera to draw your chart.';
      $('measurements').innerHTML = picked.map(r => `<article><strong>${escape(r.camera)}</strong><br>${escape(r.codec)} · ${escape(r.configuration)}<br>${escape(r.settings)}<br>Source: ${escape(r.source)}<br>Video bitrate: ${fmt(r.lowMbps)} – ${fmt(r.highMbps)} Mbps</article>`).join('');
      if (!picked.length) {svgText=''; $('chart').textContent='No cameras selected.'; return;}
      const width=1120,left=360,right=140,top=112,rowHeight=48,bottom=124;
      const height=top+picked.length*rowHeight+bottom;
      const max=Math.ceil(Math.max(...picked.map(r=>r.highMbps))/10)*10;
      const x=n=>left+n/max*(width-left-right);
      const parts=[`<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Selected 4K30 front-camera video bitrates" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}"><rect width="${width}" height="${height}" fill="white"/><g font-family="Arial, sans-serif" fill="#182733"><text x="560" y="34" font-size="26" font-weight="700" text-anchor="middle">4K30 Front-Camera Bitrate Comparison</text><text x="560" y="65" font-size="17" text-anchor="middle">${escape($('subtitle').value)}</text>`];
      for(let tick=0;tick<=max;tick+=10) parts.push(`<path d="M${x(tick)} ${top-16}V${height-bottom+4}" stroke="#e0e5eb"/><text x="${x(tick)}" y="${height-bottom+30}" text-anchor="middle" font-size="16">${tick}</text>`);
      picked.forEach((r,i)=>{
        const y=top+i*rowHeight,highlight=r.id==='viofo-t340';
        const value=r.highMbps-r.lowMbps>=0.15 ? `${fmt(r.lowMbps)} – ${fmt(r.highMbps)}` : fmt(r.highMbps);
        const words=r.camera.split(' '),lines=[''];
        for(const word of words) {if((lines[lines.length-1]+' '+word).trim().length>32) lines.push(word);else lines[lines.length-1]=(lines[lines.length-1]+' '+word).trim();}
        const label=lines.map((line,j)=>`<tspan x="${left-18}" dy="${j?20:0}">${escape(line)}</tspan>`).join('');
        parts.push(`<text x="${left-18}" y="${y+6-(lines.length-1)*10}" text-anchor="end" font-size="18" font-weight="${highlight?'700':'400'}">${label}</text><rect x="${left}" y="${y-14}" width="${x(r.highMbps)-left}" height="28" fill="${highlight?'#ee8a19':'#23839d'}"/>`);
        if(r.highMbps>r.lowMbps) parts.push(`<path d="M${x(r.lowMbps)} ${y}H${x(r.highMbps)}M${x(r.lowMbps)} ${y-8}V${y+8}M${x(r.highMbps)} ${y-8}V${y+8}" stroke="#182733" stroke-width="2"/>`);
        parts.push(`<text x="${x(r.highMbps)+10}" y="${y+6}" font-size="18" font-weight="700">${value}</text>`);
      });
      parts.push(`<text x="${(left+width-right)/2}" y="${height-bottom+60}" text-anchor="middle" font-size="18">Video Bitrate (Mbps)</text><text x="28" y="${height-36}" font-size="15">Vortex Radar testing library · Video bitrate only, audio excluded.</text><text x="28" y="${height-12}" font-size="15">T340 A/B are separate units. Codecs and setups differ. Higher bitrate alone doesn't establish better image quality.</text></g><metadata>${escape(JSON.stringify(picked))}</metadata></svg>`);
      svgText=parts.join(''); $('chart').innerHTML=svgText;
    }
    function download(blob, extension) {
      const url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url; a.download=`front-camera-bitrates.${extension}`; a.click(); setTimeout(()=>URL.revokeObjectURL(url),10000);
    }
    $('search').addEventListener('input',()=>{for(const label of $('choices').querySelectorAll('label')) label.hidden=!label.dataset.search.includes($('search').value.toLowerCase());});
    // Hidden overrides display:flex on the camera labels.
    const style=document.createElement('style'); style.textContent='.choice[hidden]{display:none}';document.head.append(style);
    $('all').onclick=()=>{selected=new Set(rows.map(r=>r.key));render();};
    $('clear').onclick=()=>{selected.clear();render();};
    $('t340').onclick=()=>{selected=new Set(['t340-a','t340-b']);render();};
    $('sort').onchange=render;
    $('subtitle').addEventListener('input',render);
    $('svg').onclick=()=>download(new Blob([svgText],{type:'image/svg+xml'}),'svg');
    $('png').onclick=async()=>{
      const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'}));
      try {
        const image=new Image(); image.src=url; await image.decode();
        const canvas=document.createElement('canvas'); canvas.width=image.width*2;canvas.height=image.height*2;
        canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
        const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
        if(!blob) throw new Error('PNG export failed.'); download(blob,'png');
      } catch(error) {$('status').textContent=error.message;} finally {URL.revokeObjectURL(url);}
    };
    $('share').onclick=async()=>{try {await navigator.clipboard.writeText(location.href);$('status').textContent='Chart link copied.';}catch {$('status').textContent='Copy the chart link from your address bar.';}};
    render();
  } catch(error) {$('choices').textContent='Camera measurements could not be loaded. Reload to try again.';$('status').textContent=error.message;}
})();
