/**
 * Plotquake Official Brand Design System & Color Tokens
 * 
 * Signature Color: Plotquake Golden Amber (#E5A158 / #F6C383)
 * Exact palette sampled directly from the official logo doorway beam of light.
 * Tone: Amarelo alaranjado, quase dourado, luxuoso e cinematográfico.
 */

export const PLOTQUAKE_THEME = {
  colors: {
    // Primary Signature Gold / Amber (Direto do feixe de luz do logo)
    primary: '#E5A158',           // Golden Amber (Amarelo alaranjado quase dourado)
    primaryLight: '#F6C383',      // Luminous Doorway Gold (Ponto alto de luz)
    primaryDeep: '#BF6D2C',       // Rich Amber Bronze
    primaryGlow: 'rgba(229, 161, 88, 0.40)',
    primaryHighlight: 'rgba(229, 161, 88, 0.45)', // Marca-texto dourado elegante para jornais
    primaryBorder: 'rgba(229, 161, 88, 0.85)',
    primaryPillBg: 'rgba(229, 161, 88, 0.15)',
    primaryPillBorder: 'rgba(229, 161, 88, 0.35)',

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
    goldGlow: '0 0 20px rgba(229, 161, 88, 0.45)',
    goldGlowIntense: '0 0 35px rgba(246, 195, 131, 0.70)',
    cinematicDrop: '0 25px 70px rgba(0, 0, 0, 0.85)',
  },
} as const;
