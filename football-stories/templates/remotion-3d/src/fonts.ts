import { continueRender, delayRender, staticFile } from "remotion";

const loaded = new Set<string>();

// Load a font file from /public and block rendering until it is ready,
// so no frame is ever captured with a fallback font.
export const useFont = (family: string, file: string) => {
  if (loaded.has(family)) return;
  const handle = delayRender(`font ${family}`);
  const face = new FontFace(family, `url(${staticFile(file)})`);
  face
    .load()
    .then((f) => {
      document.fonts.add(f);
      loaded.add(family);
      continueRender(handle);
    })
    .catch(() => continueRender(handle));
};
