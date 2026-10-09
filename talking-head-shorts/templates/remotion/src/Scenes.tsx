// Scenes.tsx  YOUR graphics: one line per scene, `s(from, to, <Component .../>)`, times in output seconds.
// Delete a line to remove a scene. m("name") is a mark from timeline.json and throws a clear error if it is missing.
// build.py never overwrites this file once it exists in <slug>/anim/src/. The list is empty by default (no graphics).
//
// MENU (uncomment a line, keep the trailing comma; marks each one needs are named in m("...")):
//   s(0, TL.hook, <Hook />),                                                         // breaking-news slam; needs TL.hook > 0
//   s(TL.hook, m("makeup"), <NewsTicker />),                                          // ticker until the makeup mark
//   s(m("makeup"), m("makeup_end"), <Makeup image="store.jpg" logo="logo.png" />),
//   s(m("reveal2"), m("reveal_end"), <RevealTitle logo="logo.png" />),
//   s(m("list"), m("engine") - 0.04, <ShoppingList />),
//   s(m("engine"), m("engine") + 1.36, <Engine />),
//   s(m("card"), m("kyunki"), <CreditCard pinAt={m("pin") - m("card")} logo="logo.png" />),
//   s(m("kyunki"), m("kangali"), <BalanceChip dur={m("kangali") - m("kyunki")} />),
//   s(m("kangali"), m("kangali") + 0.85, <Kangali />),
//   s(m("paglu"), m("salary") - 0.04, <ShareSheet sendAt={m("send") - m("paglu")} />),
//   s(m("salary"), m("shaheed"), <Salary t1={m("tareekh1") - m("salary")} t2={m("tareekh2") - m("salary")} logo="logo.png" />),
//   s(m("shaheed"), m("shaheed_end"), <Shaheed />),
//   s(m("hunger") - 0.05, m("hunger_end") - 0.05, <Hunger />),
//   s(m("traffic"), m("traffic_end"), <TrafficMap />),
//   s(m("bada_stamp"), m("bada"), <NayaStamp />),
//   s(m("bada"), m("bada_end"), <BadaSize />),
//   s(m("maps"), m("maps_end"), <MapsNav logo="logo.png" />),
//   s(m("share2"), m("chat_end"), <ChatCTA />),
//   s(m("end"), TL.total, <EndCard logo="logo.png" />),
//   // formerly removable ones
//   s(m("road"), m("road_end"), <RoadClosed />),
//   s(m("maut"), m("maut_end"), <MautCrowd logo="logo.png" />),
//   s(m("langar"), m("langar_end"), <Langar paneerAt={m("paneer") - m("langar")} />),
//   s(m("lion"), m("lion_end"), <Lion s={m("lion")} chunkId="B1" roarAt={m("roar")} />),
//   s(m("barbaadi"), m("barbaadi_end"), <Barbaadi shuruAt={m("shuru") - m("barbaadi")} dur={m("barbaadi_end") - m("barbaadi")} />),
// Every text, colour and amount is a prop (see the header of each file in ./kit); images/logos are files in anim/public/ (<slug>/assets/).
import React from "react";
import { TL, M, Seq } from "./kit";
import {
  Hook, NewsTicker, Makeup, RevealTitle, ShoppingList, Engine, CreditCard, BalanceChip, Kangali, ShareSheet, Salary, Shaheed, Hunger,
  TrafficMap, NayaStamp, BadaSize, MapsNav, ChatCTA, EndCard, RoadClosed, MautCrowd, Langar, Lion, Barbaadi,
} from "./kit";

const m = (name: string): number => {
  const v = M[name];
  if (typeof v !== "number") throw new Error(`Scenes.tsx: timeline.json has no mark "${name}". Marks: ${Object.keys(M).join(", ") || "(none)"}`);
  return v;
};
const s = (from: number, to: number, el: React.ReactNode) => <Seq key={`${from}-${to}`} from={from} to={to}>{el}</Seq>;

// keep the imports referenced so unused-import tooling stays quiet while the list is empty
void [TL, m, Hook, NewsTicker, Makeup, RevealTitle, ShoppingList, Engine, CreditCard, BalanceChip, Kangali, ShareSheet, Salary, Shaheed, Hunger, TrafficMap, NayaStamp, BadaSize, MapsNav, ChatCTA, EndCard, RoadClosed, MautCrowd, Langar, Lion, Barbaadi];

const scenes = (): React.ReactNode[] => [
];

export const Scenes: React.FC = () => <>{scenes()}</>;
