# ffmpeg / Pillow recipes and gotchas

Everything here is what `render.py` does internally, written out so you can do a
one-off by hand or extend the script. Verified on Homebrew ffmpeg 9 on macOS.

## Environment facts
- Homebrew ffmpeg has **no drawtext** (no freetype). All text is Pillow RGBA PNGs composited with `overlay`.
- Fonts: `/System/Library/Fonts/Supplemental/Impact.ttf` (headlines), `.../Arial Bold.ttf` (sub-lines),
  `/System/Library/Fonts/Apple Color Emoji.ttc` (emoji: draw at size 160 with `embedded_color=True`, then resize).
- `pip` on this machine may point at a private index that returns 401: always `pip install -i https://pypi.org/simple pillow`, inside a venv (PEP 668).
- Available filters that matter: crop scale zoompan setpts reverse areverse atempo minterpolate loop split concat vstack hstack xfade fade tpad overlay tile fps amix adelay afade loudnorm volumedetect anullsrc sine blackdetect.

## Inspect
```
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames:format=duration -of default=nw=1 in.mp4
```

## Find the moment (contact sheets)
```
# one frame every 4 s of a 100 s window, 5x5 tiles
ffmpeg -ss 200 -t 100 -i in.mp4 -vf "fps=1/4,scale=384:-1,tile=5x5:padding=4:margin=4:color=white" -frames:v 1 sheet.png
# dense: 2 fps over 10 s
ffmpeg -ss 262 -t 10 -i in.mp4 -vf "fps=2,scale=320:-1,tile=6x4" -frames:v 1 fine.png
```
`sheets.py` does the same with time labels and a pixel grid for reading crop x.

## Reframe 16:9 → 9:16
- Full height window: `crop=608:1080:X:0,scale=1080:1920,setsar=1` with `X = centre − 304` (clamp 0…1312).
- Tighter on a face: `crop=500:889:X:Y`.
- Pan: `crop=608:1080:x='896-200*t/1.7':y=0` (x may be any expression in `t`).
- Split screen: two `crop=608:540:X:Y,scale=1080:960` halves → `vstack`.
- Centred fallback: `crop=ih*9/16:ih`.

## Time effects
- Freeze: extract a PNG (`-ss T -frames:v 1`), then `-loop 1 -t D -i frame.png` + `scale=2160:3840,zoompan=z='1+0.06*on/N':d=N:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=25` (upscaling 2× first removes zoompan jitter).
- Simple slow-mo: `setpts=2*PTS` + `anullsrc` audio (or `atempo=0.5`).
- Smooth slow-mo: `minterpolate=fps=75:mi_mode=mci:mc_mode=aobmc:vsbmc=1,setpts=3*PTS` (slow to encode; feed it ≤ 1 s).
- Reverse: `reverse,setpts=N/25/TB,setpts=1.25*PTS` with `-af areverse,atempo=0.8`.
- Boomerang: `split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0,loop=loop=1:size=64:start=0,setpts=N/25/TB`.
- Punch-zoom pulse: `scale=w='1080*(1+0.07*abs(sin(t*8)))':h=-2:eval=frame,crop=1080:1920`.

## Assemble
- Encode every segment identically: `-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r 25` and `-c:a aac -b:a 160k -ar 48000 -ac 2`; silent segments get `-f lavfi -t D -i anullsrc=r=48000:cl=stereo`.
- Pin frames: `-frames:v N -t D` with `N = floor(D*25 + 0.5)` on every segment, or the concat drifts by a frame per cut. Not Python `round()`: it is banker's rounding, so 82.5 becomes 82 and the cut lands a frame early.
- Stretching: `setpts=k*PTS` on N frames yields kN−k+1 frames, one short of k·N. Read one extra source frame (`-t D+0.04`) and pin with `-frames:v`. For `minterpolate` pad by two frames (3x on N frames measured 3N−5); more pulls the blurred footage after the window into the interpolation and ghosts the tail.
- Never put an output `-t` on a stretched or interpolated segment: ffmpeg drops the final duplicated frame and the segment comes up one short even when enough input was read. Pin video with `-frames:v` and bound silent audio with the `anullsrc -t D` input instead. Count frames of every segment (`ffprobe -count_frames`) before concatenating.
- Concat demuxer: `file '/abs/path.mp4'` lines → `ffmpeg -f concat -safe 0 -i list.txt -c copy raw.mp4`.
- Captions: each PNG is an input `-loop 1 -framerate 25 -t TOTAL -i ov.png` and `overlay=0:0:eof_action=pass:enable='between(t,A,B)'`. A single-frame PNG input without `-loop 1 -t TOTAL` never shows mid-video.
- Audio: `[0:a]volume=0.9[a0]; [bed]volume=0.22,afade=t=out:st=..:d=..[a1]; sine=f=48:d=0.6 → afade,adelay=8160|8160[a2]; amix=inputs=3:duration=first:normalize=0, loudnorm=I=-14:TP=-1.5:LRA=11`. Without loudnorm the mix peaks around −10 dB and sounds quiet next to other Shorts.
- Final: `-movflags +faststart -t TOTAL`.

## Verify
```
ffmpeg -i out.mp4 -af volumedetect -vf blackdetect=d=0.25 -f null -     # peak ≈ −1.5 dB, mean ≈ −18…−21 dB
ffprobe -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 out.mp4   # = 25 × seconds
```
Then look at the check sheet (`check.py`), not just the numbers: subject in frame at every cut, faces not cropped, captions readable and inside safe zones, the last frame cuts back to the opening beat so it loops.

## Timing that worked (20 s Ronaldo v2, for scale)
Live miss 3.3 s → close-up 1.7 → celebration 1.6 → ref 0.9 → graphic + freeze 1.5 → comic beats 2 + 2.5 + 2.5 → reaction 1.5 → slow-mo out 2.5. Text changes every 1.5–2.5 s; a bass hit lands on the freeze and on the biggest reveal.
