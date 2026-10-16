import {AbsoluteFill, Audio, Sequence, interpolate, useCurrentFrame} from 'remotion';
import {KenBurnsImage} from '../components/KenBurnsImage';
import {MarketChart} from '../components/MarketChart';
import {QuoteCard} from '../components/QuoteCard';
import {ActMarker} from '../components/ActMarker';
import {BrollPlayer} from '../components/BrollPlayer';
import {MediaCaption} from '../components/MediaCaption';
import {NewspaperPop} from '../components/NewspaperPop';
import {resolveMedia} from '../media';
import type {DocumentaryEpisode, DocumentaryScene, DocumentaryShot} from '../types';

export type DocumentaryProps = {episode: DocumentaryEpisode};

const DISSOLVE_FRAMES = 12;

const Shot = ({shot, previousSrc, canDissolve}: {shot: DocumentaryShot; previousSrc?: string; canDissolve: boolean}) => {
  const frame = useCurrentFrame();
  const opacity = canDissolve && shot.transition === 'dissolve'
    ? interpolate(frame, [0, DISSOLVE_FRAMES], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
    : 1;
  const background = shot.src ?? previousSrc;
  return <AbsoluteFill style={{opacity}}>
    {shot.type === 'video' && shot.src ? (
      <BrollPlayer src={shot.src} durationInFrames={shot.durationInFrames}
        trimBefore={shot.trimBefore} playbackRate={shot.playbackRate} muted={shot.muted}
        volume={shot.volume} fit={shot.fit} focus={shot.focus} caption={shot.caption}
        label={shot.sourceLabel} reconstruction={shot.reconstruction} vintageFilter={shot.vintageFilter} />
    ) : background ? (
      <KenBurnsImage src={background} durationInFrames={shot.durationInFrames}
        focus={shot.focus} zoomStart={shot.zoomStart} zoomEnd={shot.zoomEnd} motion={shot.motion}
        fit={shot.fit} caption={shot.type === 'image' ? shot.caption : undefined}
        sourceLabel={shot.sourceLabel} reconstruction={shot.reconstruction} />
    ) : <AbsoluteFill style={{background: 'radial-gradient(ellipse at 65% 40%, #1c2634, #05070c 78%)'}} />}
    {shot.type === 'chart' && shot.chart && <MarketChart {...shot.chart} delay={5} />}
    {shot.type === 'quote' && shot.quote && <QuoteCard quote={shot.quote.text}
      author={shot.quote.author} title={shot.quote.title} year={shot.quote.year} delay={5} />}
  </AbsoluteFill>;
};

const SceneCaption = ({caption, durationInFrames}: {caption: string; durationInFrames: number}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [Math.max(1, durationInFrames - 18), durationInFrames], [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{opacity}}><MediaCaption caption={caption} /></AbsoluteFill>;
};

const Scene = ({scene, captionFrom = 10}: {scene: DocumentaryScene; captionFrom?: number}) => (
  <AbsoluteFill>
    {scene.audioSrc && <Audio src={resolveMedia(scene.audioSrc)} volume={1} />}
    {scene.shots.map((shot, index) => {
      const next = scene.shots[index + 1];
      // The preceding picture stays under a dissolve, avoiding a flash to black.
      const overlap = next?.transition === 'dissolve' ? DISSOLVE_FRAMES : 0;
      const duration = Math.min(scene.durationInFrames - shot.from, shot.durationInFrames + overlap);
      const previousImage = scene.shots.slice(0, index).reverse().find((s) => s.src && s.type !== 'video')?.src;
      return <Sequence key={shot.id} name={shot.caption ?? shot.id} from={shot.from} durationInFrames={Math.max(1, duration)}>
        <Shot shot={shot} previousSrc={previousImage} canDissolve={index > 0} />
      </Sequence>;
    })}
    {scene.newspaper && <Sequence name="Document evidence" from={scene.newspaper.from}
      durationInFrames={scene.newspaper.durationInFrames}>
      <NewspaperPop {...scene.newspaper} />
    </Sequence>}
    {scene.caption && captionFrom < scene.durationInFrames - 30 && <Sequence from={captionFrom}
      durationInFrames={Math.min(165, scene.durationInFrames - captionFrom)}>
      <SceneCaption caption={scene.caption} durationInFrames={Math.min(165, scene.durationInFrames - captionFrom)} />
    </Sequence>}
  </AbsoluteFill>
);

export const Documentary = ({episode}: DocumentaryProps) => {
  const frame = useCurrentFrame();
  const fps = episode.fps || 30;
  const music = typeof episode.audio?.music === 'string'
    ? {src: episode.audio.music, volume: 0.13}
    : episode.audio?.music;
  // A global clock keeps fades correct when a short score loops.
  const masterFade = Math.min(
    interpolate(frame, [0, fps * 1.7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
    interpolate(frame, [Math.max(0, episode.durationInFrames - fps * 3), episode.durationInFrames], [1, 0],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
  );
  const sceneWindows = episode.acts.flatMap((act) => act.scenes.map((scene) => ({
    from: act.startFrame + scene.startFrame,
    until: act.startFrame + scene.startFrame + scene.durationInFrames,
    voiced: Boolean(scene.audioSrc),
  })));
  const isVoiced = sceneWindows.some((scene) => scene.voiced && frame >= scene.from && frame < scene.until);

  return (
    <AbsoluteFill style={{backgroundColor: '#05070c', fontFamily: 'Arial, Helvetica, sans-serif'}}>
      {music && <Audio src={resolveMedia(music.src)} loop
        volume={(music.volume ?? 0.13) * masterFade * (isVoiced ? 1 : 1.22)} />}
      {episode.audio?.narration && <Audio src={resolveMedia(episode.audio.narration)} volume={1} />}
      {episode.audio?.effects?.map((effect, index) => <Sequence key={index} from={effect.from}
        durationInFrames={effect.durationInFrames}>
        <Audio src={resolveMedia(effect.src)} volume={effect.volume ?? 0.16} />
      </Sequence>)}
      {episode.acts.map((act, index) => {
        const markerFrom = act.markerFrom ?? (index === 0 ? Math.min(14 * fps, Math.floor(act.durationInFrames / 3)) : 15);
        const markerDuration = Math.max(1, Math.min(135, act.durationInFrames - markerFrom));
        return <Sequence key={act.id} name={act.actTitle} from={act.startFrame} durationInFrames={act.durationInFrames}>
          {act.scenes.map((scene, sceneIndex) => (
            <Sequence key={scene.id} name={scene.id} from={scene.startFrame} durationInFrames={scene.durationInFrames}>
              <Scene scene={scene} captionFrom={sceneIndex === 0 && index > 0 ? markerFrom + markerDuration + 8 : 10} />
            </Sequence>
          ))}
          <Sequence from={markerFrom} durationInFrames={markerDuration}>
            <ActMarker actNumber={act.actNumber} actTitle={act.actTitle} subtitle={act.subtitle}
              durationInFrames={markerDuration} />
          </Sequence>
        </Sequence>;
      })}
      {/* Subtle framing and channel signature, consistent across all sources. */}
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 48, background: '#020305'}} />
        <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: 48, background: '#020305'}} />
        <div style={{position: 'absolute', top: 80, right: 80, color: 'rgba(255,255,255,0.58)',
          fontSize: 18, letterSpacing: 4, fontWeight: 700, textShadow: '0 1px 8px #000'}}>
          PLOT<span style={{color: 'rgba(229,161,88,0.85)'}}>QUAKE</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
