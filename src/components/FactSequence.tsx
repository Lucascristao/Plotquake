import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

export type FactSequenceProps = {
  title: string;
  subtitle?: string;
  steps: {label: string; detail?: string}[];
  source?: string;
  durationInFrames?: number;
};

/** An editorial explanation of sourced facts, never an imitation of an original document. */
export const FactSequence = ({title, subtitle, steps, source, durationInFrames = 600}: FactSequenceProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const duration = Math.max(1, durationInFrames);
  const progress = Math.min(1, Math.max(0, frame / duration));
  const entrance = interpolate(frame, [0, Math.min(fps * .65, duration * .08)], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const rowGap = steps.length > 3 ? 150 : 177;
  const lastReveal = duration * .65;
  const firstReveal = duration * .09;
  const revealAt = (index: number) => firstReveal + index / Math.max(1, steps.length - 1) * (lastReveal - firstReveal);
  const lineProgress = interpolate(frame, [firstReveal, Math.max(firstReveal + 1, lastReveal)], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const lineHeight = Math.max(0, steps.length - 1) * rowGap;

  return <div style={{position: 'absolute', inset: 0, opacity: entrance,
    overflow: 'hidden', fontFamily: 'Arial, Helvetica, sans-serif',
    background: 'radial-gradient(ellipse at 75% 35%, #17202c 0%, #080d16 48%, #030712 100%)'}}>
    <div style={{position: 'absolute', inset: 0,
      transform: `translate(${(progress - .5) * 10}px, ${(0.5 - progress) * 6}px) scale(${1 + progress * .006})`}}>
      <div style={{position: 'absolute', top: 151, left: 144, right: 144}}>
        <div style={{width: 78, height: 3, background: PLOTQUAKE_THEME.colors.primary, marginBottom: 23}} />
        <div style={{fontSize: 46, fontWeight: 700, lineHeight: 1.18, letterSpacing: -.7,
          color: PLOTQUAKE_THEME.colors.textPrimary}}>{title}</div>
        {subtitle && <div style={{fontSize: 27, lineHeight: 1.35, color: '#b6c1ce', marginTop: 13}}>{subtitle}</div>}
      </div>
      <div style={{position: 'absolute', top: steps.length > 3 ? 319 : 333, left: 154, right: 170}}>
        <div style={{position: 'absolute', left: 11, top: 24, width: 2, height: lineHeight,
          background: 'rgba(148,163,184,.22)'}} />
        <div style={{position: 'absolute', left: 11, top: 24, width: 2, height: lineHeight,
          transform: `scaleY(${lineProgress})`, transformOrigin: 'top center',
          background: PLOTQUAKE_THEME.colors.primary}} />
        {steps.map((step, index) => {
          const begin = revealAt(index);
          const reveal = interpolate(frame, [begin, begin + Math.min(fps * .8, duration * .055)], [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return <div key={`${index}-${step.label}`} style={{position: 'absolute', top: index * rowGap,
            left: 0, right: 0, opacity: reveal, transform: `translateY(${(1 - reveal) * 12}px)`}}>
            <div style={{position: 'absolute', left: 3, top: 16, width: 18, height: 18, borderRadius: '50%',
              background: PLOTQUAKE_THEME.colors.primary, boxShadow: '0 0 20px rgba(229,161,88,.16)'}} />
            <div style={{paddingLeft: 64}}>
              <div style={{fontSize: 46, lineHeight: 1.15, fontWeight: 700, letterSpacing: -.6,
                color: PLOTQUAKE_THEME.colors.primaryLight}}>{step.label}</div>
              {step.detail && <div style={{fontSize: 32, lineHeight: 1.3, color: '#e2e8f0',
                maxWidth: 1430, marginTop: 10}}>{step.detail}</div>}
            </div>
          </div>;
        })}
      </div>
      {source && <div style={{position: 'absolute', left: 218, right: 170, bottom: 111,
        fontSize: 19, lineHeight: 1.35, color: '#94a3b8'}}>{source}</div>}
    </div>
  </div>;
};
