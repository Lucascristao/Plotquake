/* Typeset the cover with the actual OFL-licensed Anton Regular font. */
const fs = require('node:fs');
const path = require('node:path');
const moduleFlag = process.argv.indexOf('--canvas-module');
const {createCanvas, loadImage, GlobalFonts} = require(moduleFlag < 0 ? '@napi-rs/canvas' : process.argv[moduleFlag + 1]);

async function main() {
  const root = path.resolve(__dirname, '..');
  const font = path.join(root, 'public/assets/fonts/Anton-Regular.ttf');
  const background = path.join(root, 'public/assets/images/itt-thumbnail-v3-base.png');
  const output = path.join(root, 'public/assets/images/itt-thumbnail-v3.png');
  if (!GlobalFonts.registerFromPath(font, 'PlotquakeAnton')) throw new Error('Anton font registration failed.');
  const image = await loadImage(background);
  const canvas = createCanvas(1280, 720);
  const ctx = canvas.getContext('2d');
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';
  const lines = [{text: 'CIA', size: 174, top: 113, color: '#FFFFFF'},
    {text: 'CONNECTION', size: 91, top: 293, color: '#E5A158'}];
  for (const line of lines) {
    ctx.font = `${line.size}px PlotquakeAnton`;
    if (ctx.measureText(line.text).width > 561) throw new Error(`Cover line exceeds safe bounds: ${line.text}`);
    ctx.fillStyle = line.color;
    ctx.fillText(line.text, 40, line.top);
  }
  fs.writeFileSync(output, canvas.toBuffer('image/png'));
  console.log(JSON.stringify({output, width: 1280, height: 720, font: 'Anton Regular', weight: 400, lines}));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
