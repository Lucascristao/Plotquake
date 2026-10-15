import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

type QuoteCardProps = {
  quote: string;
  author: string;
  title?: string;
  year?: string;
  delay?: number;
};

export const QuoteCard = ({
  quote,
  author,
  title,
  year,
  delay = 0,
}: QuoteCardProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: {damping: 16, stiffness: 90, mass: 0.8},
  });

  const opacity = interpolate(progress, [0, 0.7], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const translateY = interpolate(progress, [0, 1], [40, 0], {
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
        background: 'rgba(3, 7, 18, 0.78)',
        backdropFilter: 'blur(10px)',
        zIndex: 25,
        opacity,
      }}
    >
      <div
        style={{
          maxWidth: 1100,
          padding: '60px 70px',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderLeft: `8px solid ${PLOTQUAKE_THEME.colors.primary}`,
          borderRadius: 24,
          boxShadow: '0 30px 100px rgba(0,0,0,0.7), -10px 0 35px rgba(255, 85, 0, 0.3)',
          transform: `translateY(${translateY}px)`,
        }}
      >
        <div
          style={{
            color: PLOTQUAKE_THEME.colors.primary,
            fontSize: 72,
            fontFamily: '"Georgia", serif',
            lineHeight: 0.5,
            marginBottom: 20,
            textShadow: '0 0 20px rgba(255, 85, 0, 0.5)',
          }}
        >
          "
        </div>

        <div
          style={{
            color: '#f8fafc',
            fontSize: 44,
            fontWeight: 700,
            lineHeight: 1.28,
            letterSpacing: -0.5,
            marginBottom: 36,
            fontStyle: 'italic',
          }}
        >
          {quote}
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderTop: '1px solid rgba(255, 255, 255, 0.14)',
            paddingTop: 20,
          }}
        >
          <div>
            <div style={{color: '#ffffff', fontSize: 28, fontWeight: 800}}>
              {author}
            </div>
            {title && (
              <div style={{color: '#94a3b8', fontSize: 20, fontWeight: 500}}>
                {title}
              </div>
            )}
          </div>

          {year && (
            <div
              style={{
                color: PLOTQUAKE_THEME.colors.primary,
                fontSize: 24,
                fontWeight: 800,
                backgroundColor: 'rgba(255, 85, 0, 0.15)',
                border: '1px solid rgba(255, 85, 0, 0.35)',
                padding: '6px 18px',
                borderRadius: 12,
              }}
            >
              {year}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
