import { useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

const loaded = new Set<string>();
const pending = new Set<string>();

// True once the font is in document.fonts (text measuring in kit/props.tsx waits for it;
// document.fonts.check() can't be used: it returns true for a family it has never heard of).
export const fontReady = (family: string) => loaded.has(family);

// Load a font file from /public and block rendering until it is ready, so no frame is ever
// captured with a fallback font. Re-renders once it lands, so text sized by measuring
// (Title, Bubble, Stamp, Badge) is measured with the real font before the frame is taken.
export const useFont = (family: string, file: string) => {
  const [, bump] = useState(0);
  if (loaded.has(family) || pending.has(family)) return;
  pending.add(family);
  const handle = delayRender(`font ${family}`);
  const face = new FontFace(family, `url(${staticFile(file)})`);
  face
    .load()
    .then((f) => {
      document.fonts.add(f);
      loaded.add(family);
      bump((n) => n + 1);
      requestAnimationFrame(() => continueRender(handle));
    })
    .catch(() => continueRender(handle));
};
