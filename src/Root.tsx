import {Composition} from 'remotion';
import {Documentary} from './compositions/Documentary';
import preparedEpisode from './episodes/renderEpisode.json';
import type {DocumentaryEpisode} from './types';

const episode = preparedEpisode as DocumentaryEpisode;

export const RemotionRoot = () => (
  <>
    <Composition id="Documentary" component={Documentary}
      durationInFrames={episode.durationInFrames} fps={episode.fps || 30} width={1920} height={1080}
      defaultProps={{episode}}
      calculateMetadata={({props}) => ({
        durationInFrames: props.episode.durationInFrames,
        fps: props.episode.fps || 30,
      })} />
    <Composition id="OpeningPreview" component={Documentary}
      durationInFrames={Math.min(60 * (episode.fps || 30), episode.durationInFrames)}
      fps={episode.fps || 30} width={1920} height={1080}
      defaultProps={{episode}} />
  </>
);
