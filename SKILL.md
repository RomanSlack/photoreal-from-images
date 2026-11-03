---
name: photoreal-from-images
description: Make photoreal plants, stones, ground covers and materials for Blender/Cycles scenes the way The Gym project does - generated reference photos (cut-out leaf cards, tileable texture photos with a height map) on procedural geometry built in Python, checked in a 30-second studio render before the full scene. Use when the user wants realistic foliage, trees, bonsai, topiary, grass, heath, boulders, river stones, bark, moss or any natural material in a 3D scene, says a material "looks CG / plastic / fake / like code", or asks how to get photoreal results cheaply.
---

# Photoreal from images

The rule that made everything in The Gym look real: **the realism comes from images, the structure comes from code.**
Patterns drawn in code (noise for lichen, flat green quads for leaves, a colour for bark) always read as CG. A generated
photo of the real thing, cut out or made tileable, read as real the first time (Roman: "monstera 100x better").
Geometry stays procedural (one seed = one plant, no two alike), because shape, density and placement are what code is good at.

## The loop (every element: a leaf, a bark, a boulder, a ground cover)

1. **Reference first.** Look at real photos of the thing (habit, close-up, how it sits in the ground). Write down the
   numbers you will build from: leaf length and aspect, stems per clump, height, how deep a boulder is buried.
2. **Generate the surface photo** with the `imagegen` skill (Gemini Nano Banana 2 is cheap and good at this):
   - **Leaves**: one leaf per image, *flat-lay from directly above on pure white, tip up, petiole at the bottom, even soft
     studio light, no shadow*. Then cut it out:
     `python3 <skill-dir>/scripts/leaf_cutout.py maps/<plant> leaf1.webp leaf2.webp --solid --delight`
     (RGBA card + bump + atlas.json with aspect, petiole joint and midrib position). `--delight` for small glossy leaves:
     the studio highlight otherwise repeats on every card and reads milky.
   - **Surfaces** (bark, granite, lichen, heath floor, river stone): *orthographic close-up, filling the frame evenly, flat
     overcast light, no shadows, no horizon, no focal point*. Then
     `python3 <skill-dir>/scripts/make_tileable.py src.webp maps/<name> --px 4096` (de-lit, wrap-blended, + height map).
3. **Build the geometry in Python** (bpy + numpy + bmesh, no `bpy.ops` in loops: in a big scene each op re-evaluates
   everything, 77 rocks took minutes; bmesh takes a second):
   - leaf cards: a 3x3 grid per leaf, UVs 0..1, cupped along the midrib, placed at the atlas' petiole joint
   - fine things (needles, grass blades, heather scale leaves, plume bristles) are geometry, not texture
   - stones: an ellipsoid sheared by 6-14 random planes (split granite faces), 1 light smoothing pass (worn edges, not
     eggs), low-frequency lumps; sunk 30-40 % into the ground; clustered (one big + smaller ones leaning on it)
   - ground covers: a handful of clump "protos" scattered with Geometry Nodes instancing (density per m2)
4. **Material**: box-projected image at its real-world size, per-object tone/hue from Object Info > Random (no two stones or
   leaves the same), bump from the height map, a darker earthy band where it meets the ground, moss only on up-facing tops.
   **No plastic clear coat** on leaves; roughness 0.3-0.5, a little translucency.
5. **Studio check (30 s)**: a tiny scene (sky + sun, the thing on the ground texture, 64 samples, 1600x900) rendered
   *before* the full scene. Iterate here. Only when it reads right, render it in the real scene.
6. **Look at it beside the reference** and name what is wrong in words (too round, too white, reads as grass). Fix the one
   biggest thing, re-render the studio check. Typical fixes that worked: de-light the leaf photo; darker tone range for
   stones; heather as twigs with scale leaves instead of ribbons; a stone bed with no plants on it so the stones read.

## Gotchas that cost us time

- Blender 5 Mix node: `outputs[0]` is the *float* result; use `outputs["Result"]` (by name it picks the enabled socket).
  Linking `outputs[0]` turned every stone white.
- A generated photo of one leaf repeated 500 times shows its highlight 500 times: de-light it.
- Texture packs with tile grout lines (e.g. "granite_tile") put grid lines on boulders. Use gridless sources.
- Things laid on terrain must follow the *designed* grade, not the raw ground: hidden old mounds made paving slabs tilt.
  Push the ground mesh down under paving instead of lifting the paving.
- `BVHTree.FromObject` fails on objects with a Geometry Nodes modifier: build from the base mesh.
- Render one camera per Blender process under a memory cap (`systemd-run --user --scope -p MemoryMax=12G ... nice -n 19`):
  batching cameras once grew to 16 GB and the OOM killer took the desktop session. Only render on the GPU.
- Never overwrite an image: every render is `<name>_vNNN.jpg`; the history is how you see progress.

## Why this costs so little (Claude usage + API money)

This project ran for weeks of long sessions on a $200 Claude Max plan and barely used any of it. The reasons are structural:

- **Claude writes code; the computer does the heavy work.** Geometry, texture processing and every render happen locally
  (Blender Cycles on the GPU, numpy/OpenCV). A million leaves cost the same tokens as ten: it is one script. Claude's tokens
  go to short code edits, short command outputs and looking at a few images.
- **Variants are free.** A generator with a seed makes 100 different pines for zero extra tokens or API calls.
- **Images are generated once and reused forever.** One heath photo covers 900 m2 of ground; one granite photo every
  boulder. The whole gym project used ~134 generated images, about **$15 of image API** in total
  (Gemini Nano Banana 2 at ~$0.07-0.15 each); textures beyond that are free (Poly Haven CC0).
- **Cheap feedback loop.** The 30-second studio render catches problems before a 10-minute scene render, and Claude reads
  one downsized JPG (about 1-2k tokens) instead of logs or many frames.
- **Terse tool output.** Commands print only what is needed (`grep` the log for `[time]`, `kept`, `Traceback`), never full
  Blender logs. Long jobs run in the background and notify when done instead of being polled.
- **Measure before optimising.** `[time]` lines showed 3 of 10 minutes per shot were ground ray-casts through the whole
  building: a BVH of the ground mesh made it 1 second. Caching expensive results (a grown birch grove saved to a .blend and
  appended) does the same.
- **Subagents only for real fan-out work** (e.g. web research with image downloads), not for things a few tool calls do.
- **Everything is saved and committed as it goes** (versioned renders, one commit per change), so nothing is ever redone
  after a crash or a lost context.

## Gallery (all made this way, rendered locally)

See `gallery/`: `bonsai.jpg`, `cloud_pine.jpg`, `birch.jpg`, `topiary.jpg`, `boulders.jpg`, `heath.jpg`, `entrance.jpg`,
and `heath_texture.jpg` (one generated photo, made tileable, that is the whole heath floor).

## Files

| File | What it does |
| --- | --- |
| `scripts/leaf_cutout.py` | generated leaf photos -> RGBA leaf cards + bump + atlas.json |
| `scripts/make_tileable.py` | a generated surface photo -> tileable colour map + height map (de-lit, wrap-blended) |

Requires Python 3 with numpy + opencv-python, Blender 4.2+ (tested on 5.x) with Cycles on a GPU, and an image generator
(the `imagegen` skill, or any Gemini / OpenAI image API).
