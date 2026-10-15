import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

type NewspaperPopProps = {
  headline: string;
  subheadline?: string;
  date: string;
  source: string;
  highlightWords?: string[];
  delay?: number;
};

export const NewspaperPop = ({
  headline,
  subheadline,
  date,
  source,
  highlightWords = [],
  delay = 0,
}: NewspaperPopProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const pop = spring({
    frame: frame - delay,
    fps,
    config: {damping: 14, stiffness: 100, mass: 0.8},
  });

  const scale = interpolate(pop, [0, 1], [0.82, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const rotation = interpolate(pop, [0, 1], [-4, -0.8], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const opacity = interpolate(pop, [0, 0.6], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'grid',
        placeItems: 'center',
        background: 'rgba(5, 7, 12, 0.7)',
        backdropFilter: 'blur(8px)',
        zIndex: 20,
        opacity,
      }}
    >
      <div
        style={{
          width: 1200,
          padding: '48px 64px',
          backgroundColor: '#f4ede2', // Aged paper color
          color: '#1a1815',
          boxShadow: '0 30px 90px rgba(0,0,0,0.85), inset 0 0 100px rgba(0,0,0,0.06)',
          border: '1px solid rgba(0,0,0,0.25)',
          transform: `scale(${scale}) rotate(${rotation}deg)`,
          fontFamily: '"Georgia", serif',
        }}
      >
        {/* Newspaper Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            borderBottom: '4px double #1a1815',
            paddingBottom: 16,
            marginBottom: 28,
          }}
        >
          <div>
            <div
              style={{
                fontSize: 48,
                fontWeight: 900,
                letterSpacing: 2,
                textTransform: 'uppercase',
                fontFamily: '"Times New Roman", serif',
              }}
            >
              {source}
            </div>
            <div style={{fontSize: 16, letterSpacing: 1, textTransform: 'uppercase'}}>
              Special Historical Edition • Vol. LXXIV
            </div>
          </div>
          <div style={{fontSize: 20, fontWeight: 700, fontStyle: 'italic'}}>
            {date}
          </div>
        </div>

        {/* Main Headline */}
        <div
          style={{
            fontSize: 56,
            fontWeight: 900,
            lineHeight: 1.12,
            letterSpacing: -1,
            textTransform: 'uppercase',
            textAlign: 'center',
            marginBottom: 20,
            borderBottom: '2px solid #1a1815',
            paddingBottom: 24,
          }}
        >
          {headline}
        </div>

        {/* Subheadline with Golden Amber highlighter marker effect (logo-matched) */}
        {subheadline && (
          <div
            style={{
              fontSize: 28,
              lineHeight: 1.35,
              fontWeight: 600,
              textAlign: 'center',
              color: '#1a1815',
              padding: '12px 24px',
              backgroundColor: PLOTQUAKE_THEME.colors.primaryHighlight,
              display: 'inline-block',
              width: '100%',
              boxSizing: 'border-box',
              borderRadius: 4,
            }}
          >
            {subheadline}
          </div>
        )}
      </div>
    </div>
  );
};
