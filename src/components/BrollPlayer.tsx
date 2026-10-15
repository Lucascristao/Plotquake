import {OffthreadVideo, staticFile, useCurrentFrame, interpolate} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';

type BrollPlayerProps = {
  src: string;
  durationInFrames: number;
  label?: string;
  vintageFilter?: boolean;
};

export const BrollPlayer = ({
  src,
  durationInFrames,
  label = 'ARCHIVAL FOOTAGE',
  vintageFilter = true,
}: BrollPlayerProps) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [0, 10, durationInFrames - 10, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  return (
    <div
      style={{
        position: 'relative',
        width: 1920,
        height: 1080,
        backgroundColor: '#000000',
        overflow: 'hidden',
        opacity,
      }}
    >
      {/* Video Stream */}
      <OffthreadVideo
        src={src.startsWith('http') ? src : staticFile(src)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          filter: vintageFilter
            ? 'contrast(1.2) brightness(0.9) sepia(0.25) saturate(0.85)'
            : 'none',
        }}
      />

      {/* Cinematic Letterbox (Cinemascope 2.39:1 feel) */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 60,
          backgroundColor: '#000000',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 60,
          backgroundColor: '#000000',
        }}
      />

      {/* Subtle Scanlines & Grain */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle at center, transparent 30%, rgba(0,0,0,0.7) 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Plotquake Orange Archive Badge */}
      <div
        style={{
          position: 'absolute',
          top: 90,
          left: 90,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '10px 22px',
          backgroundColor: 'rgba(10, 13, 20, 0.85)',
          borderLeft: `5px solid ${PLOTQUAKE_THEME.colors.primary}`,
          backdropFilter: 'blur(10px)',
          borderRadius: '0 8px 8px 0',
        }}
      >
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            backgroundColor: PLOTQUAKE_THEME.colors.primary,
            boxShadow: `0 0 12px ${PLOTQUAKE_THEME.colors.primary}`,
          }}
        />
        <span
          style={{
            color: '#ffffff',
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: 2,
            textTransform: 'uppercase',
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
};
