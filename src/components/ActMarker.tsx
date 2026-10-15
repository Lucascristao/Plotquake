import {interpolate, useCurrentFrame} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

type ActMarkerProps = {
  actNumber: number | string;
  actTitle: string;
  subtitle?: string;
  durationInFrames: number;
};

/** Chapter reveal over a moving shot: narration and picture continue underneath. */
export const ActMarker = ({actNumber, actTitle, subtitle, durationInFrames}: ActMarkerProps) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 16, durationInFrames - 20, durationInFrames], [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const movement = interpolate(frame, [0, 22], [18, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', inset: 0, opacity, pointerEvents: 'none', zIndex: 30,
      background: 'linear-gradient(0deg, rgba(2,5,9,0.88), rgba(2,5,9,0.3) 39%, transparent 67%)'}}>
      <div style={{position: 'absolute', left: 104, right: 190, bottom: 165,
        transform: `translateY(${movement}px)`}}>
        <div style={{color: PLOTQUAKE_THEME.colors.primaryLight, fontSize: 19, fontWeight: 700,
          letterSpacing: 5, textTransform: 'uppercase', marginBottom: 19}}>
          {typeof actNumber === 'number' ? `CHAPTER ${String(actNumber).padStart(2, '0')}` : actNumber}
        </div>
        <div style={{width: 88, height: 3, background: PLOTQUAKE_THEME.colors.primary, marginBottom: 23}} />
        <div style={{color: '#fff', fontSize: actTitle.length > 38 ? 58 : 70, fontWeight: 750,
          letterSpacing: -1.8, lineHeight: 1.08, maxWidth: 1500, textShadow: '0 3px 28px #000'}}>
          {actTitle}
        </div>
        {subtitle && <div style={{color: '#d1d5db', fontSize: 25, lineHeight: 1.4,
          maxWidth: 1200, marginTop: 18}}>{subtitle}</div>}
      </div>
    </div>
  );
};
