// Compatibility export for projects that previously imported the 14-second demo.
// The prepared episode is the only timeline; historical claims live in episodes/.
import preparedEpisode from './renderEpisode.json';
import type {DocumentaryEpisode} from '../types';

export type {DocumentaryEpisode, DocumentaryAct, DocumentaryScene} from '../types';
export const pilotEpisode = preparedEpisode as DocumentaryEpisode;
