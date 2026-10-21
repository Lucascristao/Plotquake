/* Set the cover's type in the actual Anton Regular face, with original proportions. */
const fs = require('node:fs');
const path = require('node:path');
const moduleFlag = process.argv.indexOf('--canvas-module');
const {createCanvas, loadImage, GlobalFonts} = require(moduleFlag < 0 ? '@napi-rs/canvas' : process.argv[moduleFlag + 1]);

async function main() {
  const root = path.resolve(__dirname, '..');
  if (!GlobalFonts.registerFromPath(path.join(root, 'public/assets/fonts/Anton-Regular.ttf'), 'PlotquakeAnton')) {
    throw new Error('Anton Regular font registration failed.');
  }
  const base = await loadImage(path.join(root, 'public/assets/images/sts51a-thumbnail-base.png'));
  const canvas = createCanvas(1280, 720);
  const context = canvas.getContext('2d');
  context.drawImage(base, 0, 0, 1280, 720);
  context.textAlign = 'left';
  context.textBaseline = 'top';
  const lines = [{text: 'FOR', size: 158, y: 177, color: '#FFFFFF'},
    {text: 'SALE', size: 190, y: 337, color: '#E5A158'}];
  for (const line of lines) {
    context.font = `${line.size}px PlotquakeAnton`;
    if (context.measureText(line.text).width > 456) throw new Error('Type exceeds cover safe area.');
    context.fillStyle = line.color;
    context.fillText(line.text, 57, line.y);
  }
  const output = path.join(root, 'public/assets/images/sts51a-thumbnail.png');
  fs.writeFileSync(output, canvas.toBuffer('image/png'));
  console.log(JSON.stringify({output, width: 1280, height: 720, font: 'Anton Regular', weight: 400, lines}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
