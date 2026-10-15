import {staticFile} from 'remotion';

export const resolveMedia = (src: string): string => {
  if (/^(https?:|data:|blob:)/i.test(src)) return src;
  return staticFile(src.replace(/\\/g, '/').replace(/^\/+/, ''));
};
