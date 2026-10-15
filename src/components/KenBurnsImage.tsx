import {Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

type KenBurnsProps = {
  src: string;
  durationInFrames: number;
  zoomDirection?: 'in' | 'out';
  panDirection?: 'left' | 'right' | 'up' | 'down';
  caption?: string;
  sourceLabel?: string;
};

export const KenBurnsImage = ({
  src,
  durationInFrames,
  zoomDirection = 'in',
  panDirection = 'left',
  caption,
  sourceLabel,
}: KenBurnsProps) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  const scale = interpolate(
    frame,
    [0, durationInFrames],
    zoomDirection === 'in' ? [1.02, 1.16] : [1.16, 1.02],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const translateX = interpolate(
    frame,
    [0, durationInFrames],
    panDirection === 'left' ? [0, -35] : panDirection === 'right' ? [0, 35] : [0, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const translateY = interpolate(
    frame,
    [0, durationInFrames],
    panDirection === 'up' ? [0, -25] : panDirection === 'down' ? [0, 25] : [0, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  return (
    <div
      style={{
        position: 'relative',
        width,
        height,
        overflow: 'hidden',
        backgroundColor: '#05070c',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          transform: `scale(${scale}) translate(${translateX}px, ${translateY}px)`,
          transformOrigin: 'center center',
        }}
      >
        <Img
          src={src}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      </div>

      {/* Cinematic Vignette */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.72) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Film grain / Subtle scanline overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%)',
          backgroundSize: '100% 4px',
          opacity: 0.18,
          pointerEvents: 'none',
        }}
      />

      {/* Documentary Caption Lower Third with Golden Amber Accent */}
      {(caption || sourceLabel) && (
        <div
          style={{
            position: 'absolute',
            bottom: 60,
            left: 80,
            padding: '16px 28px',
            backgroundColor: 'rgba(9, 13, 20, 0.85)',
            backdropFilter: 'blur(12px)',
            borderLeft: `5px solid ${PLOTQUAKE_THEME.colors.primary}`,
            borderRadius: '0 12px 12px 0',
            boxShadow: '0 10px 40px rgba(0,0,0,0.5), -5px 0 20px rgba(229, 161, 88, 0.3)',
          }}
        >
          {caption && (
            <div
              style={{
                color: '#ffffff',
                fontSize: 26,
                fontWeight: 700,
                letterSpacing: 0.5,
              }}
            >
              {caption}
            </div>
          )}
          {sourceLabel && (
            <div
              style={{
                color: '#94a3b8',
                fontSize: 18,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 1.5,
                marginTop: 4,
              }}
            >
              {sourceLabel}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
