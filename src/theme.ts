/**
 * Plotquake Official Brand Design System & Color Tokens
 * 
 * Signature Color: Plotquake Orange (#FF5500 / #FF6B00)
 * Rule: Any colorful UI accent, border, highlight, indicator, glow, or kinetic badge
 * in Plotquake videos MUST strictly use Plotquake Orange.
 */

export const PLOTQUAKE_THEME = {
  colors: {
    // Primary Signature Orange
    primary: '#FF5500',
    primaryLight: '#FF6B00',
    primaryGlow: 'rgba(255, 85, 0, 0.45)',
    primaryHighlight: 'rgba(255, 85, 0, 0.45)', // Neon orange marker for newspaper pop
    primaryBorder: 'rgba(255, 85, 0, 0.85)',

    // Deep Cinematic Dark Neutrals
    background: '#030712',
    cardBackground: '#0b0f19',
    overlayDark: 'rgba(5, 7, 12, 0.75)',

    // Typography & Contrast Whites/Grays
    textPrimary: '#FFFFFF',
    textSecondary: '#F8FAFC',
    textMuted: '#94A3B8',
    textDark: '#1a1815',
  },
  shadows: {
    orangeGlow: '0 0 20px rgba(255, 85, 0, 0.5)',
    orangeGlowIntense: '0 0 35px rgba(255, 85, 0, 0.8)',
    cinematicDrop: '0 25px 70px rgba(0, 0, 0, 0.85)',
  },
} as const;
