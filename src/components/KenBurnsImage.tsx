import {AbsoluteFill, Img, interpolate, useCurrentFrame} from 'remotion';
import {resolveMedia} from '../media';
import type {FocusPoint} from '../types';
import {MediaCaption} from './MediaCaption';

type KenBurnsProps = {
  src: string;
  durationInFrames: number;
  focus?: FocusPoint;
  zoomStart?: number;
  zoomEnd?: number;
  motion?: 'push' | 'pull' | 'pan-left' | 'pan-right' | 'still';
  fit?: 'cover' | 'contain';
  caption?: string;
  sourceLabel?: string;
  reconstruction?: boolean;
  zoomDirection?: 'in' | 'out';
  panDirection?: 'left' | 'right' | 'up' | 'down';
};

export const KenBurnsImage = ({
  src, durationInFrames, focus = {x: 0.5, y: 0.5}, zoomStart, zoomEnd,
  motion = 'push', fit = 'cover', caption, sourceLabel, reconstruction,
  zoomDirection, panDirection,
}: KenBurnsProps) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const pulling = motion === 'pull' || zoomDirection === 'out';
  const stationary = motion === 'still';
  const scaleA = zoomStart ?? (stationary ? 1.035 : pulling ? 1.14 : 1.045);
  const scaleB = zoomEnd ?? (stationary ? 1.035 : pulling ? 1.045 : 1.14);
  const scale = scaleA + (scaleB - scaleA) * progress;
  const panX = motion === 'pan-left' || panDirection === 'left' ? 1 :
    motion === 'pan-right' || panDirection === 'right' ? -1 : 0;
  const panY = panDirection === 'up' ? 1 : panDirection === 'down' ? -1 : 0;
  const x = Math.max(0, Math.min(1, focus.x)) * 100;
  const y = Math.max(0, Math.min(1, focus.y)) * 100;
  const mediaSrc = resolveMedia(src);

  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#05070c'}}>
      {fit === 'contain' && (
        <Img src={mediaSrc} style={{position: 'absolute', inset: '-5%', width: '110%',
          height: '110%', objectFit: 'cover', filter: 'blur(32px) brightness(0.25) saturate(0.55)'}} />
      )}
      <AbsoluteFill style={{transform: `scale(${scale}) translate(${panX * (0.5 - progress) * 2}%, ${panY * (0.5 - progress) * 1.4}%)`,
        transformOrigin: `${x}% ${y}%`}}>
        <Img src={mediaSrc} style={{width: '100%', height: '100%', objectFit: fit,
          objectPosition: `${x}% ${y}%`, filter: 'contrast(1.05) saturate(0.88)',
          ...(fit === 'contain' ? {padding: '86px 100px', boxSizing: 'border-box'} : {})}} />
      </AbsoluteFill>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 44%, transparent 42%, rgba(0,0,0,0.48) 100%)', pointerEvents: 'none'}} />
      <MediaCaption caption={caption} sourceLabel={sourceLabel} reconstruction={reconstruction} />
    </AbsoluteFill>
  );
};
