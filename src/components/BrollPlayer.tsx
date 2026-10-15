import {AbsoluteFill, OffthreadVideo} from 'remotion';
import {resolveMedia} from '../media';
import type {FocusPoint} from '../types';
import {MediaCaption} from './MediaCaption';

type BrollPlayerProps = {
  src: string;
  durationInFrames: number;
  trimBefore?: number;
  trimAfter?: number;
  playbackRate?: number;
  muted?: boolean;
  volume?: number;
  fit?: 'cover' | 'contain';
  focus?: FocusPoint;
  caption?: string;
  label?: string;
  reconstruction?: boolean;
  vintageFilter?: boolean;
};

/** A directed excerpt: no automatic fades, invented dates, or archive stamp. */
export const BrollPlayer = ({src, trimBefore = 0, trimAfter, playbackRate = 1,
  muted = true, volume = 0.2, fit = 'cover', focus = {x: 0.5, y: 0.5},
  caption, label, reconstruction, vintageFilter = false}: BrollPlayerProps) => (
  <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#05070c'}}>
    <OffthreadVideo src={resolveMedia(src)} trimBefore={trimBefore} trimAfter={trimAfter}
      playbackRate={playbackRate} muted={muted} volume={volume}
      style={{width: '100%', height: '100%', objectFit: fit,
        objectPosition: `${focus.x * 100}% ${focus.y * 100}%`,
        filter: vintageFilter ? 'contrast(1.1) brightness(0.92) sepia(0.15) saturate(0.7)' : 'contrast(1.04) saturate(0.9)'}} />
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 44%, transparent 46%, rgba(0,0,0,0.4) 100%)', pointerEvents: 'none'}} />
    <MediaCaption caption={caption} sourceLabel={label} reconstruction={reconstruction} />
  </AbsoluteFill>
);
