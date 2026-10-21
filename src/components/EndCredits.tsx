import {AbsoluteFill, Sequence, interpolate, useCurrentFrame} from 'remotion';
import type {DocumentaryEndCredits} from '../types';

const CreditCard = ({card, fadeInFrames, fadeOutFrames}: {
  card: DocumentaryEndCredits['cards'][number]; fadeInFrames: number; fadeOutFrames: number;
}) => {
  const frame = useCurrentFrame();
  const fade = Math.min(fadeInFrames, fadeOutFrames, Math.floor(card.durationInFrames / 3));
  const opacity = interpolate(frame, [0, fade, card.durationInFrames - fade, card.durationInFrames], [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: '120px 190px',
    boxSizing: 'border-box', opacity, color: '#FFFFFF', textAlign: 'center'}}>
    <div style={{fontSize: 25, fontWeight: 400, letterSpacing: 5, marginBottom: 60}}>{card.heading}</div>
    <div style={{display: 'flex', flexDirection: 'column', gap: 42, width: '100%'}}>
      {card.entries.map((entry, index) => <div key={index} style={{fontSize: 38, lineHeight: 1.45,
        fontWeight: 400, overflowWrap: 'anywhere'}}>
        {entry.lines.map((line, lineIndex) => <div key={lineIndex}>{line}</div>)}
      </div>)}
    </div>
  </AbsoluteFill>;
};

export const EndCredits = ({credits}: {credits: DocumentaryEndCredits}) => (
  <AbsoluteFill style={{backgroundColor: '#000000', fontFamily: 'Arial, Helvetica, sans-serif'}}>
    {credits.cards.map((card, index) => <Sequence key={index} from={card.from} durationInFrames={card.durationInFrames}>
      <CreditCard card={card} fadeInFrames={credits.fadeInFrames} fadeOutFrames={credits.fadeOutFrames} />
    </Sequence>)}
  </AbsoluteFill>
);
