import {interpolate, useCurrentFrame} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

type QuoteCardProps = {quote: string; author: string; title?: string; year?: string; delay?: number};

/** A restrained quotation superimposed on a relevant photograph or archive shot. */
export const QuoteCard = ({quote, author, title, year, delay = 0}: QuoteCardProps) => {
  const frame = useCurrentFrame();
  const entrance = interpolate(frame - delay, [0, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
    padding: '160px 130px', background: 'linear-gradient(90deg, rgba(3,7,13,0.92), rgba(3,7,13,0.72) 70%, rgba(3,7,13,0.4))',
    opacity: entrance}}>
    <div style={{maxWidth: 1370, borderLeft: `4px solid ${PLOTQUAKE_THEME.colors.primary}`, paddingLeft: 40,
      transform: `translateX(${(1 - entrance) * 12}px)`}}>
      <div style={{color: PLOTQUAKE_THEME.colors.primaryLight, fontSize: 88, fontFamily: 'Georgia, serif', height: 69, lineHeight: 1}}>“</div>
      <div style={{color: '#f8fafc', fontSize: quote.length > 180 ? 44 : 54, fontFamily: 'Georgia, serif',
        lineHeight: 1.3, letterSpacing: -0.7, marginBottom: 34}}>{quote}</div>
      <div style={{display: 'flex', gap: 24, alignItems: 'baseline'}}>
        <div style={{color: '#fff', fontSize: 25, fontWeight: 700}}>{author}</div>
        {year && <div style={{color: PLOTQUAKE_THEME.colors.primaryLight, fontSize: 22}}>{year}</div>}
      </div>
      {title && <div style={{color: '#a8b3c2', fontSize: 20, marginTop: 9}}>{title}</div>}
    </div>
  </div>;
};
