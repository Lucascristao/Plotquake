import {interpolate, useCurrentFrame} from 'remotion';
import {PLOTQUAKE_THEME} from '../theme';
import type {DocumentaryChart} from '../types';

type MarketChartProps = DocumentaryChart & {delay?: number; data?: {label: string; percentage: number; color?: string}[]};

export const MarketChart = ({title, subtitle, year, values, data, suffix = '%', maxValue, source, delay = 0}: MarketChartProps) => {
  const frame = useCurrentFrame();
  const points = values ?? (data ?? []).map((item, i) => ({
    label: item.label, value: item.percentage, color: item.color,
    highlight: i === 0,
  }));
  const limit = maxValue ?? (suffix === '%' ? 100 : Math.max(1, ...points.map((item) => item.value)) * 1.12);
  const opacity = interpolate(frame - delay, [0, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
      padding: '115px 110px', background: 'linear-gradient(90deg, rgba(3,7,13,0.92), rgba(3,7,13,0.82) 63%, rgba(3,7,13,0.36))', opacity}}>
      <div style={{width: 1160, padding: '34px 0', borderTop: `3px solid ${PLOTQUAKE_THEME.colors.primary}`}}>
        {year && <div style={{fontSize: 20, color: PLOTQUAKE_THEME.colors.primaryLight, letterSpacing: 4, fontWeight: 700,
          marginBottom: 18}}>{year}</div>}
        <div style={{fontSize: 45, fontWeight: 700, color: '#fff', letterSpacing: -1.2, lineHeight: 1.18}}>{title}</div>
        {subtitle && <div style={{fontSize: 22, marginTop: 12, color: '#aeb8c6'}}>{subtitle}</div>}
        <div style={{display: 'grid', gap: points.length > 4 ? 20 : 32, marginTop: 40}}>
          {points.map((item, index) => {
            const progress = interpolate(frame - delay - index * 7, [10, 49], [0, 1],
              {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            const color = item.highlight ? PLOTQUAKE_THEME.colors.primary : (item.color ?? '#576579');
            const width = Math.min(100, Math.max(0, item.value / limit * 100)) * progress;
            return <div key={item.label}>
              <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 25, fontWeight: 600, color: '#f8fafc', marginBottom: 11}}>
                <span>{item.label}</span>
                <span style={{color: item.highlight ? PLOTQUAKE_THEME.colors.primaryLight : '#c0c8d3'}}>
                  {Number(item.value.toFixed(1)).toLocaleString('en-US')}{suffix}
                </span>
              </div>
              <div style={{height: 14, background: 'rgba(255,255,255,0.075)'}}>
                <div style={{height: '100%', width: `${width}%`, background: color,
                  boxShadow: item.highlight ? '0 0 18px rgba(229,161,88,0.22)' : undefined}} />
              </div>
            </div>;
          })}
        </div>
        {source && <div style={{fontSize: 17, color: '#94a3b8', marginTop: 33}}>{source}</div>}
      </div>
    </div>
  );
};
