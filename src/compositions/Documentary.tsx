import {AbsoluteFill, Sequence, Audio, staticFile} from 'remotion';
import {KenBurnsImage} from '../components/KenBurnsImage';
import {NewspaperPop} from '../components/NewspaperPop';
import {MarketChart} from '../components/MarketChart';
import {QuoteCard} from '../components/QuoteCard';
import {ActMarker} from '../components/ActMarker';
import {BrollPlayer} from '../components/BrollPlayer';
import type {DocumentaryEpisode} from '../episodes/pilotEpisode';

type DocumentaryProps = {
  episode: DocumentaryEpisode;
};

export const Documentary = ({episode}: DocumentaryProps) => {
  return (
    <AbsoluteFill style={{backgroundColor: '#030712'}}>
      {/* 1. Background Cinematic Tension Score */}
      {episode.audio?.music && (
        <Audio
          src={staticFile(episode.audio.music)}
          volume={0.35}
        />
      )}

      {/* 2. Primary English Voice Narration (Starts at frame 30 after Act title) */}
      {episode.audio?.narration && (
        <Sequence from={25}>
          <Audio
            src={staticFile(episode.audio.narration)}
            volume={1.0}
          />
        </Sequence>
      )}

      {/* 3. Visual Acts and Scenes */}
      {episode.acts.map((act) => {
        let currentFrameOffset = 0;

        return (
          <Sequence key={act.id} from={0} durationInFrames={act.durationInFrames}>
            {/* Act Introduction Marker (first 55 frames) */}
            <Sequence from={0} durationInFrames={55}>
              <ActMarker
                actNumber={act.actNumber}
                actTitle={act.actTitle}
                subtitle={act.subtitle}
                durationInFrames={55}
              />
            </Sequence>

            {/* Scenes inside the Act */}
            {act.scenes.map((scene) => {
              const fromFrame = currentFrameOffset;
              currentFrameOffset += scene.durationInFrames;

              return (
                <Sequence
                  key={scene.id}
                  from={fromFrame}
                  durationInFrames={scene.durationInFrames}
                >
                  {scene.type === 'broll' && scene.videoSrc && (
                    <BrollPlayer
                      src={scene.videoSrc}
                      durationInFrames={scene.durationInFrames}
                      label={scene.sourceLabel}
                    />
                  )}

                  {scene.type === 'kenburns' && scene.image && (
                    <KenBurnsImage
                      src={scene.image}
                      durationInFrames={scene.durationInFrames}
                      zoomDirection={scene.zoom}
                      panDirection={scene.pan}
                      caption={scene.caption}
                      sourceLabel={scene.sourceLabel}
                    />
                  )}

                  {scene.type === 'newspaper' && scene.newspaper && (
                    <NewspaperPop
                      headline={scene.newspaper.headline}
                      subheadline={scene.newspaper.subheadline}
                      date={scene.newspaper.date}
                      source={scene.newspaper.source}
                      delay={6}
                    />
                  )}

                  {scene.type === 'chart' && scene.chart && (
                    <MarketChart
                      title={scene.chart.title}
                      year={scene.chart.year}
                      data={scene.chart.data}
                      delay={6}
                    />
                  )}

                  {scene.type === 'quote' && scene.quote && (
                    <QuoteCard
                      quote={scene.quote.text}
                      author={scene.quote.author}
                      title={scene.quote.title}
                      year={scene.quote.year}
                      delay={6}
                    />
                  )}
                </Sequence>
              );
            })}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
