import {interpolate, useCurrentFrame} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

/** Sparse identification, never a fake archive badge on generated material. */
export const MediaCaption = ({caption, sourceLabel, reconstruction}: {
  caption?: string; sourceLabel?: string; reconstruction?: boolean;
}) => {
  const frame = useCurrentFrame();
  const entrance = interpolate(frame, [8, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <>
    {caption && <div style={{position: 'absolute', bottom: 106, left: 92, maxWidth: 1120,
      borderLeft: `3px solid ${PLOTQUAKE_THEME.colors.primary}`, paddingLeft: 20,
      color: '#f8fafc', fontSize: 27, fontWeight: 600, lineHeight: 1.3,
      textShadow: '0 2px 12px #000, 0 0 25px #000', opacity: entrance,
      transform: `translateY(${(1 - entrance) * 8}px)`}}>{caption}</div>}
    {sourceLabel && <div style={{position: 'absolute', right: 78, bottom: 73, maxWidth: 1000,
      textAlign: 'right', color: 'rgba(255,255,255,0.65)', fontSize: 15,
      letterSpacing: 0.3, textShadow: '0 1px 6px #000', opacity: entrance}}>{sourceLabel}</div>}
    {reconstruction && <div style={{position: 'absolute', top: 82, left: 92,
      color: 'rgba(255,255,255,0.68)', fontSize: 14, letterSpacing: 2.1,
      fontWeight: 500, textShadow: '0 1px 8px #000', opacity: entrance}}>ILLUSTRATIVE RECONSTRUCTION</div>}
  </>;
};
