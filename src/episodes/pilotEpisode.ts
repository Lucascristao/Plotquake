export type DocumentaryScene = {
  id: string;
  durationInFrames: number;
  type: 'kenburns' | 'newspaper' | 'chart' | 'quote' | 'broll';
  image?: string;
  videoSrc?: string;
  zoom?: 'in' | 'out';
  pan?: 'left' | 'right' | 'up' | 'down';
  caption?: string;
  sourceLabel?: string;
  newspaper?: {
    headline: string;
    subheadline?: string;
    date: string;
    source: string;
  };
  chart?: {
    title: string;
    year: string;
    data: {label: string; percentage: number; color?: string}[];
  };
  quote?: {
    text: string;
    author: string;
    title?: string;
    year?: string;
  };
};

export type DocumentaryAct = {
  id: string;
  actNumber: number;
  actTitle: string;
  subtitle: string;
  durationInFrames: number;
  scenes: DocumentaryScene[];
};

export type DocumentaryEpisode = {
  id: string;
  title: string;
  subtitle: string;
  durationInFrames: number;
  audio?: {
    narration?: string;
    music?: string;
  };
  acts: DocumentaryAct[];
};

export const pilotEpisode: DocumentaryEpisode = {
  id: 'the-fall-of-blackberry',
  title: 'The $50 Billion Fall of BlackBerry',
  subtitle: 'How two engineers created an empire that owned 50% of the market—and lost it all.',
  durationInFrames: 420, // 14 seconds test
  audio: {
    narration: 'assets/audio/narration.wav',
    music: 'assets/audio/tension_score.wav',
  },
  acts: [
    {
      id: 'act-1',
      actNumber: 1,
      actTitle: 'The Wall Street Addiction',
      subtitle: 'In 2007, BlackBerry was not just a phone. It was power.',
      durationInFrames: 420,
      scenes: [
        {
          id: 'scene-1-broll',
          durationInFrames: 110,
          type: 'broll',
          videoSrc: 'assets/videos/archive_footage.mp4',
          sourceLabel: 'Archival Database • Wall Street Footage (2007)',
        },
        {
          id: 'scene-2-newspaper',
          durationInFrames: 100,
          type: 'newspaper',
          newspaper: {
            headline: 'BLACKBERRY CAPTURES 50% OF US SMARTPHONE MARKET',
            subheadline: 'Wall Street executives declare physical keyboard essential for global business.',
            date: 'OCTOBER 14, 2007',
            source: 'THE WALL STREET JOURNAL',
          },
        },
        {
          id: 'scene-3-chart',
          durationInFrames: 110,
          type: 'chart',
          chart: {
            title: 'Global Smartphone Market Share (2007)',
            year: '2007',
            data: [
              {label: 'BlackBerry (RIM)', percentage: 51, color: '#ff5500'},
              {label: 'Nokia (Symbian)', percentage: 34, color: '#3b82f6'},
              {label: 'Apple (iPhone 1st Gen)', percentage: 3, color: '#94a3b8'},
              {label: 'Others', percentage: 12, color: '#64748b'},
            ],
          },
        },
        {
          id: 'scene-4-quote',
          durationInFrames: 100,
          type: 'quote',
          quote: {
            text: 'It is okay, we will be fine. Apple is making a toy for kids. We make tools for real businessmen.',
            author: 'Jim Balsillie',
            title: 'Co-CEO, Research In Motion',
            year: '2007',
          },
        },
      ],
    },
  ],
};
