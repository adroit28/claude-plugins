// One import for the whole kit and the timing helpers:
//   import { ramp, Bubble, Stamp, at, endOf, lineStart, END, OUTRO_AT } from "./kit";
// The old paths (./kit/anim, ./kit/props, ./kit/overlays, ./kit/Outro, ./timing) still work.
export * from "./anim";
export * from "./overlays";
export * from "./props";
export * from "./motion";
export * from "./Outro";
export * from "./lottie";
export * from "./world";
export * from "./burst";
export * from "./fx";
export * from "./phone";
export * from "./audio";    // 0.9.0: Bed (a sound bed with per-frame volume)
export * from "./cinema";   // 0.9.0: rigTransform, CamPhoto, SlotCounter, Cloud/Stars/Wisps/Dust, mix/rnd/lerp
// ./hero3d (the opt-in three.js beat) is deliberately not exported here: import it by path so three.js is bundled only when used.
export * from "../timing";
