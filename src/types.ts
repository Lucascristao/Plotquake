/** All timing is in frames: act global, scene relative to act, shot relative to scene. */
export type FocusPoint = {x: number; y: number};

export type DocumentaryChart = {
  title: string;
  subtitle?: string;
  year?: string;
  suffix?: string;
  maxValue?: number;
  values?: {label: string; value: number; highlight?: boolean; color?: string}[];
  data?: {label: string; percentage: number; color?: string}[];
  source?: string;
};

export type DocumentaryQuote = {text: string; author: string; title?: string; year?: string};

/** Coordinates refer to the complete original clipping, from 0 to 1. */
export type NewspaperHighlightBox = {x: number; y: number; width: number; height: number};

export type DocumentaryNewspaper = {
  mode: 'clipping' | 'reconstruction';
  /** Timing relative to the scene; independent from its underlying shots. */
  from: number;
  durationInFrames: number;
  imageSrc?: string;
  headline?: string;
  subheadline?: string;
  source?: string;
  date?: string;
  sourceUrl?: string;
  highlightWords?: string[];
  highlightBoxes?: NewspaperHighlightBox[];
};

export type DocumentaryShot = {
  id: string;
  type: 'image' | 'video' | 'chart' | 'quote';
  from: number;
  durationInFrames: number;
  src?: string;
  caption?: string;
  sourceLabel?: string;
  origin?: string;
  reconstruction?: boolean;
  focus?: FocusPoint;
  zoomStart?: number;
  zoomEnd?: number;
  motion?: 'push' | 'pull' | 'pan-left' | 'pan-right' | 'still';
  fit?: 'cover' | 'contain';
  /** Source-video trim, in composition frames. */
  trimBefore?: number;
  playbackRate?: number;
  muted?: boolean;
  volume?: number;
  vintageFilter?: boolean;
  transition?: 'cut' | 'dissolve';
  chart?: DocumentaryChart;
  quote?: DocumentaryQuote;
};

export type DocumentaryScene = {
  id: string;
  startFrame: number;
  durationInFrames: number;
  narration?: string;
  audioSrc?: string;
  caption?: string;
  shots: DocumentaryShot[];
  newspaper?: DocumentaryNewspaper;
};

export type DocumentaryAct = {
  id: string;
  actNumber: number;
  actTitle: string;
  subtitle?: string;
  startFrame: number;
  durationInFrames: number;
  markerFrom?: number;
  scenes: DocumentaryScene[];
};

export type DocumentaryEpisode = {
  id: string;
  title: string;
  subtitle?: string;
  fps: number;
  durationInFrames: number;
  audio?: {
    music?: string | {src: string; volume?: number;
      /** Absolute gain over global frame windows; the last matching cue wins. */
      cues?: {from: number; durationInFrames: number; volume: number}[]};
    narration?: string;
    effects?: {src: string; from: number; durationInFrames?: number; volume?: number}[];
  };
  acts: DocumentaryAct[];
  sources?: unknown[];
  metadata?: Record<string, unknown>;
};
