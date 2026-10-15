import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const target='public/assets/media/catalog.json';
const existing=JSON.parse(fs.readFileSync(target,'utf8')).assets;
const assets=existing.filter(x=>fs.existsSync('public/'+x.src)).map(x=>({...x,
  fit:x.key.startsWith('blackberry_')||x.key==='iphone_original'?'contain':'cover',
  focus:x.key==='mike_lazaridis'||x.key==='jim_balsillie'?{x:.5,y:.34}:x.focus||{x:.5,y:.5},
}));
function addImage(key,src,credit,origin,reconstruction=false){
  if(fs.existsSync('public/'+src))assets.push({key,src,kind:'image',credit,origin,reconstruction,fit:reconstruction?'cover':'contain',focus:{x:.5,y:.5},license:reconstruction?'Original AI-assisted illustration':'CC BY',changes:'Cinematic framing and slow camera motion'});
}
addImage('abstract_reconstruction','assets/media/boardroom-reconstruction.png','Plotquake · Original illustrative reconstruction','generated',true);
addImage('abstract_reconstruction','assets/media/keyboard-reconstruction.png','Plotquake · Original illustrative reconstruction','generated',true);
addImage('office','assets/media/boardroom-reconstruction.png','Plotquake · Original illustrative reconstruction','generated',true);
addImage('blackberry_keyboard','assets/media/keyboard-reconstruction.png','Plotquake · Original illustrative reconstruction','generated',true);
addImage('blackberry_devices','assets/media/blackberry-rim957.jpg','Jarek Tuszyński · CC BY 4.0','https://commons.wikimedia.org/wiki/File:Blackberry_RIM_957_-_01.jpg');
addImage('blackberry_devices','assets/media/blackberry-850.jpg','Shiny Things / Traveler100 · CC BY 2.0','https://commons.wikimedia.org/wiki/File:Collection_of_old_phones_and_PDA-BlackBerry.jpg');
const videos=[
  {file:'office-phone.mp4',keys:['office','smartphone_crowd'],author:'Ketut Subiyanto',page:'a-man-typing-on-his-cellphone-and-laptop-4629172'},
  {file:'office-woman.mp4',keys:['office','smartphone_crowd'],author:'SHVETS production',page:'a-woman-typing-on-her-smartphone-7196196'},
  {file:'typing.mp4',keys:['office'],author:'Jep Gambardella',page:'person-typing-on-computer-7661323'},
  {file:'server-close.mp4',keys:['data_center','circuit'],author:'MrColo',page:'close-up-of-a-cpu-7140928'},
  {file:'server-room.mp4',keys:['data_center'],author:'ALL IZ Well',page:'database-storage-of-a-server-5028622'},
];
const ffprobe='node_modules/@remotion/compositor-win32-x64-msvc/ffprobe.exe';
for(const video of videos){
  const src='assets/media/'+video.file;
  if(!fs.existsSync('public/'+src))continue;
  const info=JSON.parse(execFileSync(ffprobe,['-v','error','-show_entries','format=duration:stream=width,height','-of','json','public/'+src],{encoding:'utf8'}));
  const durationSeconds=Number(info.format.duration);
  if(!Number.isFinite(durationSeconds)||durationSeconds<5)throw new Error('Incomplete video: '+src);
  for(const key of video.keys)assets.push({key,src,kind:'video',durationSeconds,credit:video.author+' · Pexels',origin:'https://www.pexels.com/video/'+video.page+'/',license:'Pexels License',licenseUrl:'https://www.pexels.com/license/',changes:'Muted illustrative footage; selected excerpt, framing and color treatment',trimStartSeconds:.3,fit:'cover'});
}
fs.writeFileSync(target,JSON.stringify({assets},null,2)+'\n');
console.log(JSON.stringify({assets:assets.length,uniqueFiles:new Set(assets.map(x=>x.src)).size,videoFiles:new Set(assets.filter(x=>x.kind==='video').map(x=>x.src)).size,keys:[...new Set(assets.map(x=>x.key))]}));
