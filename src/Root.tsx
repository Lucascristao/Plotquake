import {Composition} from 'remotion';
import {Documentary} from './compositions/Documentary';
import {pilotEpisode} from './episodes/pilotEpisode';

export const RemotionRoot = () => {
  return (
    <>
      {/* Full Documentary Composition (1920x1080 Full HD, 30fps) */}
      <Composition
        id="Documentary"
        component={Documentary}
        durationInFrames={pilotEpisode.durationInFrames}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          episode: pilotEpisode,
        }}
      />

      {/* Act 1 Preview Composition for Fast Testing */}
      <Composition
        id="Act1"
        component={Documentary}
        durationInFrames={pilotEpisode.acts[0].durationInFrames}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          episode: {
            ...pilotEpisode,
            durationInFrames: pilotEpisode.acts[0].durationInFrames,
            acts: [pilotEpisode.acts[0]],
          },
        }}
      />
    </>
  );
};
