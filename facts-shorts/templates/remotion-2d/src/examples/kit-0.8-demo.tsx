import { Blur, CalendarFlip, Card, Confetti, ChatBubbles, Emoji, Glitch, Hero, HookProp, LOTTIE, LottieEmoji, Meter, Notify, ShareSheet, Sfx, Stamp, Title3D, Transition, ramp } from "../kit";
import { Hero3D, EarCanal3D } from "../kit/hero3d";

// WORKED EXAMPLE of the 0.8.0 kit (not imported by the Short): every new component once, on absolute seconds so it
// can be previewed against any narration (a real scene anchors to words: at("L3", "word"), see hello-phone.tsx).
// To try it: copy it over src/Scene.tsx, change "../kit" -> "./kit" and "../kit/hero3d" -> "./kit/hero3d", put any
// photo in the Short's src/ as photo.jpg, set the story's "video": {"hotCaptions": true, "music": true}, then
//   anim.py render <story> --frames 0-179   (silent preview of the first 6 s)   or   anim.py still <story> --at 2.5 4.5 8.5 ...
//
//  0.0-1.6   Title3D (extruded hook title, light sweep) + hero emoji on spring()
//  1.6       Transition "whip" (motion-blurred panel) -> Glitch slam GALTI (+ glitch sfx)
//  3.8       Stamp with a particle burst
//  5.0-7.0   Card flip-in (3D) with a LottieEmoji
//  7.2-9.2   CalendarFlip 1900 -> 1923
//  9.4-12    Meter DANGER fills while a swab emoji sweeps in on Blur (motion blur on the fast move)
// 11.8       Transition "iris"
// 12.2-14.4  Notify + ChatBubbles
// 14.8-17.4  ShareSheet (SEND fires at 16.6) then Confetti
// 18-21.2    Hero3D: ear canal, wax pushed by a swab (the one opt-in 3D beat)

export const BACKGROUND = "radial-gradient(circle at 50% 38%, #4a3320 0%, #1f150d 55%, #0d0906 100%)";
export const SPRINGY = true;   // spring() entrances for pop / Emoji / Hero / LottieEmoji / Notify (default is the old curve)
export const BEATS = [1.6, 3.8, 9.4, 14.8];

export const Overlays = ({ t }: { t: number }) => (
  <>
    <Sfx at={1.6} src="revwhoosh" vol={0.4} />
    <Sfx at={1.9} src="glitch" vol={0.5} />
    <Sfx at={3.8} src="stamp" vol={0.6} />
    <Sfx at={12.2} src="notify" vol={0.5} />
    <Sfx at={16.6} src="whoosh" vol={0.4} />
    <Sfx at={17.0} src="confetti" vol={0.4} />

    <Title3D t={t} accent="EARBUD" rest="= GALTI?" opacity={1 - ramp(t, 1.4, 1.7)} sweeps={[0.4]} />
    <Hero t={t} a={0.1} b={1.6} char="🎧" size={520} />

    <Glitch t={t} a={1.9} b={3.5} text="GALTI" sub="MYTH" />
    <Stamp t={t} a={3.8} text="NAHI" until={4.8} burst />

    <Card src="photo.jpg" t={t} a={5.0} b={7.0} flip="y" kb={0.1}>
    </Card>
    {t < 7.1 && <LottieEmoji t={t} a={5.4} data={LOTTIE.relieved} x={700} y={340} size={260} />}

    <CalendarFlip t={t} a={7.2} b={9.0} from={1900} to={1923} label="YEAR" until={9.2} />

    <Meter t={t} a={9.4} b={11.4} label="DANGER" sub="EARDRUM" icon="👂" until={11.9} />
    <Blur a={10.4} b={11.1} kind="trail" layers={5} lag={0.8}>
      {(tt) => tt < 11.9 && <Emoji t={tt} a={9.4} char="🪥" x={ramp(tt, 10.4, 11.0, -300, 520)} y={1000} size={260} />}
    </Blur>

    <Notify t={t} a={12.2} app="MESSAGES" title="Wax is not dirt" body="Your ear cleans itself" icon="💬" until={14.4} />
    <ChatBubbles t={t} a={12.4} title="FRIEND" avatar="🙂" top={650} until={14.4}
      msgs={[[12.7, false, "wait, really?"], [13.1, true, "ear cleans itself"], [13.6, false, "send me this"]]} />

    <ShareSheet t={t} a={14.8} sendAt={16.6} title="SHARE WITH" friends={[["😎", "Rahul", "#FF8A3D"], ["🙂", "Priya", "#B26BFF"], ["😄", "Amit", "#2BC4A8"], ["🤓", "Neha", "#FF4FA3"]]} until={17.6} />
    <Confetti t={t} a={17.0} />

    <Hero3D t={t} a={18.0} b={21.2}>
      <EarCanal3D t={t} a={18.0} b={21.0} />
    </Hero3D>

    <Transition kind="whip" at={1.6} color="#ffc400" />
    <Transition kind="iris" at={11.8} color="#ffc400" x={540} y={900} />
  </>
);
