import fs from 'node:fs/promises';
import path from 'node:path';

const root = process.cwd();
const out = path.join(root, 'out', 'media');
const publicDir = path.join(root, 'public', 'assets', 'media');
const headers = {'User-Agent': 'PlotquakeDocumentary/1.0 (documentary production; Wikimedia attribution retained)'};
const queries = {
  blackberry_devices: 'BlackBerry phone filetype:bitmap',
  blackberry_keyboard: 'BlackBerry 9000 keyboard filetype:bitmap',
  blackberry_curve: 'BlackBerry Curve 8520 filetype:bitmap',
  blackberry_bold: 'BlackBerry Bold 9000 filetype:bitmap',
  blackberry_storm: 'BlackBerry Storm filetype:bitmap',
  blackberry_playbook: 'BlackBerry PlayBook filetype:bitmap',
  blackberry_z10: 'BlackBerry Z10 filetype:bitmap',
  mike_lazaridis: 'Mike Lazaridis filetype:bitmap',
  jim_balsillie: 'Jim Balsillie filetype:bitmap',
  steve_jobs: 'Steve Jobs presents iPhone filetype:bitmap',
  iphone_original: 'iPhone first generation filetype:bitmap',
  iphone_modern: 'iPhone smartphone touchscreen filetype:bitmap',
  waterloo: 'Research in Motion headquarters filetype:bitmap',
  wall_street: 'New York Stock Exchange Wall Street filetype:bitmap',
  office: 'office computer workstations filetype:bitmap',
  data_center: 'data center server racks filetype:bitmap',
  circuit: 'printed circuit board electronics filetype:bitmap',
  smartphone_crowd: 'people using smartphone filetype:bitmap',
  smartphone_video: 'smartphone filetype:video',
  city_video: 'New York timelapse filetype:video',
  computer_video: 'computer circuit filetype:video',
};
const strip = (v = '') => v.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ').replace(/\s+/g, ' ').trim();
async function fetchJson(url) {
  for (let attempt=0;attempt<5;attempt++) {
    const r = await fetch(url, {headers, signal: AbortSignal.timeout(45000)});
    if (r.status === 429 && attempt < 4) {
      await new Promise(resolve=>setTimeout(resolve, Math.min(60000, Number(r.headers.get('retry-after') || 15) * 1000 + attempt * 10000)));
      continue;
    }
    if (!r.ok) throw new Error(`${r.status} ${url}`);
    return r.json();
  }
}
await fs.mkdir(out, {recursive: true});
await fs.mkdir(publicDir, {recursive: true});
if (process.argv.includes('--discover')) {
  const candidates = JSON.parse(await fs.readFile(path.join(out,'candidates.json'),'utf8').catch(()=> '{}'));
  const entries = Object.entries(queries);
  for (let i = 0; i < entries.length; i += 1) {
    await Promise.all(entries.slice(i, i + 1).map(async ([key, search]) => {
      if(candidates[key]?.length) return;
      try {
        const params = new URLSearchParams({action:'query',format:'json',generator:'search',gsrsearch:search,gsrnamespace:'6',gsrlimit:'5',prop:'imageinfo',iiprop:'url|size|mime|extmetadata',iiurlwidth:'1600'});
        const data = await fetchJson(`https://commons.wikimedia.org/w/api.php?${params}`);
        candidates[key] = Object.values(data.query?.pages || {}).sort((a,b) => a.index-b.index).map(page => {
          const info = page.imageinfo?.[0] || {};
          const meta = info.extmetadata || {};
          return {title:page.title,url:info.thumburl || info.url,original:info.url,page:info.descriptionurl,width:info.width,height:info.height,size:info.size,mime:info.mime,artist:strip(meta.Artist?.value),license:meta.LicenseShortName?.value,licenseUrl:meta.LicenseUrl?.value,description:strip(meta.ImageDescription?.value)};
        });
        await fs.writeFile(path.join(out, 'candidates.json'), JSON.stringify(candidates,null,2));
        console.log(JSON.stringify({key,candidates:candidates[key].map(x=>({title:x.title,width:x.width,height:x.height,size:x.size,license:x.license,mime:x.mime}))}));
      } catch (e) { console.log(JSON.stringify({key,error:e.message})); }
    }));
    await new Promise(resolve=>setTimeout(resolve,1200));
  }
  await fs.writeFile(path.join(out, 'candidates.json'), JSON.stringify(candidates,null,2));
} else {
  const selected = JSON.parse(await fs.readFile(path.join(out, 'selection.json'), 'utf8'));
  const assets = [];
  for (const item of selected) {
    const ext = item.mime?.startsWith('video/') ? '.webm' : /png/i.test(item.mime || '') ? '.png' : '.jpg';
    const filename = `${item.key}-${item.variant || 1}${ext}`;
    const target = path.join(publicDir, filename);
    try {
      const present = await fs.stat(target).catch(()=>null);
      if (!present?.size) {
        const response = await fetch(item.url, {headers,signal:AbortSignal.timeout(90000)});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const bytes = Buffer.from(await response.arrayBuffer());
        if (bytes.length < 4000) throw new Error('Empty or unexpectedly small media');
        await fs.writeFile(target,bytes);
      }
      assets.push({key:item.key,src:`assets/media/${filename}`,kind:item.mime?.startsWith('video/')?'video':'image',credit:`${item.artist || 'Wikimedia Commons'} · ${item.license}`,origin:item.page,license:item.license,licenseUrl:item.licenseUrl,changes:'Cinematic crop, pan, zoom and color treatment',width:item.width,height:item.height,focus:item.focus});
      console.log(`Downloaded ${filename}`);
    } catch (e) { console.log(`FAILED ${filename}: ${e.message}`); }
  }
  await fs.writeFile(path.join(publicDir, 'catalog.json'),JSON.stringify({assets},null,2));
  console.log(`${assets.length} assets saved`);
}
