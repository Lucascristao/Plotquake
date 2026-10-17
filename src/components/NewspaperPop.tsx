import {Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {resolveMedia} from '../media';
import {PLOTQUAKE_THEME} from '../theme';
import type {DocumentaryNewspaper} from '../types';

const HighlightedText = ({text, words}: {text: string; words: string[]}) => {
  const terms = [...new Set(words.filter((word) => word.trim()))].sort((a, b) => b.length - a.length);
  if (!terms.length) return <>{text}</>;
  const expression = new RegExp(`(${terms.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  const matches = new Set(terms.map((word) => word.toLocaleLowerCase('en-US')));
  return <>{text.split(expression).map((part, index) => matches.has(part.toLocaleLowerCase('en-US'))
    ? <mark key={index} style={{background: PLOTQUAKE_THEME.colors.primaryHighlight, color: 'inherit',
      padding: '0 .06em', boxDecorationBreak: 'clone'}}>{part}</mark>
    : part)}</>;
};

/** A genuine clipping stays intact. Written reconstructions always carry an editorial label. */
export const NewspaperPop = ({mode, imageSrc, headline, subheadline, date, source,
  durationInFrames, highlightWords = [], highlightBoxes = []}: DocumentaryNewspaper) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 22, stiffness: 110, mass: .8}});
  // Keep the original page readable while the camera continues to move after entry.
  const progress = Math.min(1, Math.max(0, frame / Math.max(1, durationInFrames - 1)));
  const scale = interpolate(pop, [0, 1], [.94, 1]) * interpolate(progress, [0, 1], [1, 1.018]);
  const driftX = interpolate(progress, [0, 1], [-4, 4]);
  const driftY = interpolate(progress, [0, 1], [4, -4]);
  const rotation = interpolate(progress, [0, 1], [-.5, -.25]);
  const enter = interpolate(frame, [0, 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const exit = interpolate(frame, [Math.max(0, durationInFrames - 8), durationInFrames], [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const editorial = mode === 'reconstruction';
  const label = editorial ? 'EDITORIAL RECONSTRUCTION' : 'ORIGINAL DOCUMENT';

  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: 20, background: 'rgba(5,7,12,.90)',
    zIndex: 20, opacity: Math.min(enter, exit), padding: '90px 100px', boxSizing: 'border-box'}}>
    <div style={{color: PLOTQUAKE_THEME.colors.primaryLight, fontSize: 18, letterSpacing: 3,
      fontFamily: 'Arial, Helvetica, sans-serif', fontWeight: 700}}>{label}</div>
    <div style={{transform: `translate(${driftX}px, ${driftY}px) scale(${scale}) rotate(${rotation}deg)`, boxShadow: '0 24px 90px rgba(0,0,0,.65)'}}>
      {imageSrc ? <div style={{position: 'relative', lineHeight: 0}}>
        {/* Intrinsic proportions keep normalized highlights aligned, without cropping or letterboxing. */}
        <Img src={resolveMedia(imageSrc)} style={{display: 'block', maxWidth: 1480, maxHeight: 720,
          width: 'auto', height: 'auto'}} />
        {highlightBoxes.map((box, index) => {
          const available = Math.max(1, durationInFrames - 1);
          const begin = Math.min(fps * (.7 + index * 1.25), available * .65);
          const finish = Math.min(begin + fps * .5, available * .9);
          const reveal = interpolate(frame, [begin, Math.max(begin + .01, finish)], [0, 100],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return <div key={index} style={{position: 'absolute',
          left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`,
          height: `${box.height * 100}%`, background: PLOTQUAKE_THEME.colors.primaryHighlight,
          mixBlendMode: 'multiply', pointerEvents: 'none', clipPath: `inset(0 ${100 - reveal}% 0 0)`}} />;
        })}
      </div> : <div style={{width: 1280, padding: '56px 64px', boxSizing: 'border-box',
        background: '#f4ede2', color: '#1a1815', fontFamily: 'Georgia, serif',
        borderTop: `5px solid ${PLOTQUAKE_THEME.colors.primary}`}}>
        <div style={{fontSize: 54, fontWeight: 700, lineHeight: 1.16, letterSpacing: -.7}}>
          <HighlightedText text={headline ?? ''} words={highlightWords} />
        </div>
        {subheadline && <div style={{fontSize: 29, lineHeight: 1.4, marginTop: 28}}>
          <HighlightedText text={subheadline} words={highlightWords} />
        </div>}
      </div>}
    </div>
    {(source || date) && <div style={{maxWidth: 1440, color: '#cbd5e1', fontSize: 19, lineHeight: 1.4,
      textAlign: 'center', fontFamily: 'Arial, Helvetica, sans-serif'}}>
      {editorial && source ? 'Research: ' : ''}{[source, date].filter(Boolean).join(' • ')}
    </div>}
  </div>;
};
