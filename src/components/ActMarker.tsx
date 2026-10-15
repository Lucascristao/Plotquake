import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

type ActMarkerProps = {
  actNumber: number | string;
  actTitle: string;
  subtitle?: string;
  durationInFrames: number;
};

export const ActMarker = ({
  actNumber,
  actTitle,
  subtitle,
  durationInFrames,
}: ActMarkerProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({
    frame,
    fps,
    config: {damping: 18, stiffness: 85, mass: 0.9},
  });

  const opacity = interpolate(
    frame,
    [0, 15, durationInFrames - 15, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const scale = interpolate(entrance, [0, 1], [0.94, 1], {
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
        background: 'radial-gradient(circle at center, #0f172a 0%, #030712 100%)',
        zIndex: 30,
        opacity,
      }}
    >
      {/* Seismic Golden Grid Lines */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(rgba(229, 161, 88, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(229, 161, 88, 0.08) 1px, transparent 1px)',
          backgroundSize: '120px 120px',
        }}
      />

      <div
        style={{
          textAlign: 'center',
          transform: `scale(${scale})`,
          padding: '40px 80px',
        }}
      >
        <div
          style={{
            color: PLOTQUAKE_THEME.colors.primary,
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: 6,
            textTransform: 'uppercase',
            marginBottom: 16,
            textShadow: '0 0 20px rgba(229, 161, 88, 0.5)',
          }}
        >
          {typeof actNumber === 'number' ? `ACT ${actNumber}` : actNumber}
        </div>

        <div
          style={{
            color: '#ffffff',
            fontSize: 76,
            fontWeight: 950,
            letterSpacing: -1.5,
            textTransform: 'uppercase',
            lineHeight: 1.1,
            marginBottom: 20,
            textShadow: '0 10px 40px rgba(0,0,0,0.8)',
          }}
        >
          {actTitle}
        </div>

        {subtitle && (
          <div
            style={{
              color: '#94a3b8',
              fontSize: 32,
              fontWeight: 500,
              maxWidth: 900,
              margin: '0 auto',
            }}
          >
            {subtitle}
          </div>
        )}

        <div
          style={{
            width: 140,
            height: 4,
            backgroundColor: PLOTQUAKE_THEME.colors.primary,
            margin: '36px auto 0 auto',
            borderRadius: 2,
            boxShadow: `0 0 18px ${PLOTQUAKE_THEME.colors.primary}`,
          }}
        />
      </div>
    </div>
  );
};
