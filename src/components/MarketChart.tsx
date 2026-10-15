import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

type MarketDataPoint = {
  label: string;
  percentage: number;
  color?: string;
};

type MarketChartProps = {
  title: string;
  year?: string;
  data: MarketDataPoint[];
  delay?: number;
};

export const MarketChart = ({
  title,
  year,
  data,
  delay = 0,
}: MarketChartProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({
    frame: frame - delay,
    fps,
    config: {damping: 18, stiffness: 90, mass: 0.8},
  });

  const opacity = interpolate(entrance, [0, 0.6], [0, 1], {
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
        background: 'rgba(3, 7, 18, 0.82)',
        backdropFilter: 'blur(10px)',
        zIndex: 22,
        opacity,
      }}
    >
      <div
        style={{
          width: 1000,
          padding: '48px 56px',
          backgroundColor: '#0c1322',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: 24,
          boxShadow: '0 30px 100px rgba(0,0,0,0.8)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            borderBottom: '2px solid rgba(255, 255, 255, 0.1)',
            paddingBottom: 20,
            marginBottom: 36,
          }}
        >
          <div style={{color: '#ffffff', fontSize: 36, fontWeight: 800}}>
            {title}
          </div>
          {year && (
            <div style={{color: '#f59e0b', fontSize: 28, fontWeight: 900}}>
              {year}
            </div>
          )}
        </div>

        <div style={{display: 'grid', gap: 28}}>
          {data.map((item, index) => {
            const barSpring = spring({
              frame: frame - delay - 10 - index * 6,
              fps,
              config: {damping: 16, stiffness: 80, mass: 0.9},
            });

            const barWidth = interpolate(barSpring, [0, 1], [0, item.percentage], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });

            return (
              <div key={item.label} style={{display: 'grid', gap: 10}}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    color: '#f8fafc',
                    fontSize: 24,
                    fontWeight: 700,
                  }}
                >
                  <span>{item.label}</span>
                  <span style={{color: item.color ?? '#f59e0b'}}>
                    {Math.round(barWidth)}%
                  </span>
                </div>

                <div
                  style={{
                    width: '100%',
                    height: 24,
                    backgroundColor: 'rgba(255,255,255,0.08)',
                    borderRadius: 12,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${barWidth}%`,
                      height: '100%',
                      backgroundColor: item.color ?? '#f59e0b',
                      borderRadius: 12,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
