import { Easing, Img, interpolate, staticFile } from "remotion";
import { at, lineStart, END, OUTRO_AT, LAST_T } from "../timing";
import { ramp, pulse, pop } from "../kit/anim";
import { STROKE } from "../kit/overlays";
import {
  Avatar, Badge, Bubble, Card, CountUp, Emoji, HookProp, Layer, NameTag, PAPER, Question, Rings, Shake, Sfx, Stamp, Sway, Title, clamp, vis,
} from "../kit/props";

// WORKED EXAMPLE (not imported by the Short): "Why do we say hello on the phone?", 6 lines, ~30 s.
// To use it as a starting point, copy it over src/Scene.tsx and fix the import paths ("../" -> "./").
// L1 Socho... hum phone uthate hi "Hello" kyun bolte hain?
// L2 Iska answer bahut interesting hai, kyunki telephone ke inventor toh kuch aur hi bolna chahte the.
// L3 Alexander Graham Bell chahte the ki hum "Ahoy!" bolein. Haan, wahi jo films mein pirates bolte hain.
// L4 Par 1877 mein Edison ne kaha: "Hello" bolo. Ye 10-20 feet door tak sunai deta hai, ghanti bajane ki zaroorat hi nahi.
// L5 Aur "Hello" itna chala ki kuch hi saalon mein phone operators ko hi "hello-girls" bulaya jaane laga.
// L6 Aur ahoy? Wo pirates ke paas hi reh gaya.
// Photos: telephone.png, bell.jpg, pirate.jpg, edison.jpg, switchboard.jpg (Commons, public domain).

export const BACKGROUND = "radial-gradient(circle at 50% 38%, #4a3320 0%, #1f150d 55%, #0d0906 100%)";

const T = {
  pick: 0.5,                                    // the receiver is picked up after the opening ring (story narration.lead)
  hello1: at("L1", "hello"),
  l2: lineStart("L2"), kyunki: at("L2", "kyunki"), inventor: at("L2", "inventor"), aur: at("L2", "aur"),
  l3: lineStart("L3"), ahoy: at("L3", "ahoy"), haan: at("L3", "haan"), pirates: at("L3", "pirates"),
  l4: lineStart("L4"), y1877: at("L4", "1877"), hello2: at("L4", "hello"), ye: at("L4", "ye"), feet: at("L4", "feet"),
  hai: at("L4", "hai"), ghanti: at("L4", "ghanti"), nahi: at("L4", "nahi"),
  l5: lineStart("L5"), hg: at("L5", "hellogirls"),
  l6: lineStart("L6"), wo: at("L6", "wo"),
};

export const Overlays = ({ t }: { t: number }) => {
  const loopIn = ramp(t, OUTRO_AT, OUTRO_AT + 0.4);                    // hook comes back under the badge
  const hookOp = (1 - ramp(t, T.l2 + 0.2, T.l2 + 0.6)) + loopIn;
  const ringing = t < T.pick || t > LAST_T - 0.9;
  const sail = ramp(t, T.wo, END + 0.2, 0, 1, Easing.in(Easing.quad));
  return (
    <>
      <Sfx at={0} src="ring" vol={0.45} />
      <Sfx at={T.pick} src="click" vol={0.7} />
      <Sfx at={T.l2} src="riser" vol={0.28} />
      <Sfx at={T.aur} src="bass" vol={0.6} />
      <Sfx at={T.l3 - 0.15} src="whoosh" vol={0.4} />
      <Sfx at={T.ahoy} src="horn" vol={0.5} />
      <Sfx at={T.haan} src="waves" vol={0.35} />
      <Sfx at={T.l4 - 0.15} src="whoosh" vol={0.4} />
      <Sfx at={T.y1877} src="bass" vol={0.45} />
      <Sfx at={T.hello2} src="ding" vol={0.35} />
      <Sfx at={T.ghanti} src="ding" vol={0.45} />
      <Sfx at={T.nahi} src="buzz" vol={0.3} />
      <Sfx at={T.l5 - 0.1} src="whoosh" vol={0.35} />
      <Sfx at={T.hg} src="stamp" vol={0.75} />
      <Sfx at={T.wo} src="waves" vol={0.3} />
      <Sfx at={LAST_T - 0.55} src="ring" vol={0.3} />

      {/* A. hook: ringing phone, picked up, HELLO? bubble; the "why" question mark */}
      <Title t={t} accent={'"HELLO"'} rest="HI KYUN?" opacity={(1 - ramp(t, T.l2 + 0.2, T.l2 + 0.5)) + loopIn} />
      <HookProp t={t} char="☎️" active={ringing} opacity={hookOp}
        scale={t < T.pick ? 1 : interpolate(t - T.pick, [0, 0.12, 0.3], [1, 0.92, 1], clamp)} />
      {vis(t, T.hello1, T.l2 + 0.3) && <Bubble t={t} a={T.hello1} text="HELLO?" x={700} y={520} size={130} />}
      <Question t={t} a={T.l2} b={T.kyunki} />

      {/* B. the first telephone; who invented it? */}
      <Card src="telephone.png" t={t} a={T.kyunki} b={T.l3 - 0.1} from="zoom" w={900} h={560} top={480} pos="50% 50%">
        {t >= T.inventor && (
          <div style={{ position: "absolute", left: 300, top: -330, width: 300, height: 300, borderRadius: "50%", background: "#111",
            border: "10px solid #ffc400", display: "flex", alignItems: "center", justifyContent: "center",
            transform: `scale(${pop(t, T.inventor)}) scale(${1 + 0.18 * pulse(t, T.aur)})`, fontFamily: "Anton", fontSize: 200, color: "#ffc400" }}>?</div>
        )}
      </Card>

      {/* C. Bell wanted "Ahoy!" */}
      <Shake t={t} at={T.ahoy}>
        <Card src="bell.jpg" t={t} a={T.l3} b={T.haan - 0.05} from="left" pos="50% 12%">
          <NameTag t={t} a={T.l3 + 0.25} name="ALEXANDER GRAHAM BELL" sub="TELEPHONE INVENTOR" />
        </Card>
        {vis(t, T.ahoy, T.haan + 0.1) && <Bubble t={t} a={T.ahoy} text="AHOY!" x={700} y={340} color="#0b4fd8" size={150} />}
      </Shake>

      {/* D. ...the pirate word */}
      <Sway t={t} from={T.haan}>
        <Card src="pirate.jpg" t={t} a={T.haan} b={T.l4 - 0.05} from="zoom" slam tilt={-3} pos="50% 25%" />
        {vis(t, T.haan + 0.15, T.l4) && <Bubble t={t} a={T.haan + 0.15} text="AHOY!" x={720} y={330} color="#c4161c" size={150} rot={6} />}
        {vis(t, T.pirates, T.l4) && <Emoji t={t} a={T.pirates} char="🏴‍☠️" x={120} y={210} size={170} rot={-12} />}
      </Sway>

      {/* E. 1877: Edison says "Hello" */}
      <Card src="edison.jpg" t={t} a={T.l4} b={T.ye - 0.05} from="right" pos="50% 15%">
        <NameTag t={t} a={T.l4 + 0.3} name="THOMAS EDISON" />
      </Card>
      {vis(t, T.y1877, T.ye) && <Badge t={t} a={T.y1877} text="1877" />}
      {vis(t, T.hello2, T.ye) && <Bubble t={t} a={T.hello2} text="HELLO!" x={720} y={360} color="#0a8f3c" size={150} />}

      {/* F. heard 10-20 feet away (counter across the whole phrase); no ghanti needed */}
      <Layer opacity={vis(t, T.ye - 0.05, T.l5 + 0.2) ? 1 - ramp(t, T.l5 - 0.1, T.l5 + 0.2) : 0}>
        <Avatar src="edison.jpg" t={t} a={T.ye - 0.05} x={70} y={470} />
        {t >= T.ye && <Rings t={t - T.ye} x={220 + 40} y={620} r0={120} grow={260} speed={0.9} n={3} width={12} half />}
        <CountUp t={t} a={T.ye} b={T.hai} from={10} to={20} unit="FEET" show={T.feet} />
        <Emoji t={t} a={T.ghanti} char="🔔" x={620} y={450} wobble crossAt={T.nahi} />
      </Layer>

      {/* G. hello spread: the hello-girls */}
      <Card src="switchboard.jpg" t={t} a={T.l5} b={T.l6 - 0.05} from="right" pos="50% 55%" />
      {vis(t, T.hg, T.l6) && <Stamp t={t} a={T.hg} text="HELLO-GIRLS" />}

      {/* H. ahoy stayed with the pirates */}
      <Layer opacity={vis(t, T.l6, OUTRO_AT + 0.4) ? 1 - ramp(t, OUTRO_AT, OUTRO_AT + 0.4) : 0}>
        <div style={{ position: "absolute", left: 60, top: 420, width: 440, textAlign: "center", transform: `scale(${pop(t, T.l6)})` }}>
          <div style={{ fontSize: 260, lineHeight: 1 }}>☎️</div>
          <div style={{ fontFamily: "Anton", fontSize: 120, color: "#2bd46a", ...STROKE(8) }}>HELLO ✓</div>
        </div>
        <div style={{ position: "absolute", left: 560, top: 380, width: 440, textAlign: "center",
          transform: `translate(${700 * sail}px, ${60 * sail}px) rotate(${t > T.wo ? 7 * Math.sin((t - T.wo) * 7) : 0}deg) scale(${pop(t, T.l6 + 0.15)})` }}>
          <div style={{ width: 380, height: 420, margin: "0 auto", borderRadius: 14, overflow: "hidden", border: `10px solid ${PAPER}` }}>
            <Img src={staticFile("pirate.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 22%" }} />
          </div>
          <div style={{ fontFamily: "Anton", fontSize: 110, color: "#fff", ...STROKE(8) }}>AHOY 🏴‍☠️</div>
        </div>
      </Layer>
    </>
  );
};
