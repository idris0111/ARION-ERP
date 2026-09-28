# Pet art handoff

The repository currently has **no production GLB pet or wearable assets**. The seven species entries in `frontend/src/features/pet/config.ts` are deliberately marked `assetReady: false`. The app presents an honest placeholder and keeps pet creation, chat and settings available.

Place one optimized, rigged `companion.glb` in each species directory: `cat/`, `dog/`, `fox/`, `rabbit/`, `panda/`, `bear/`, `wolf/`. Set that species' `assetReady` flag to `true` only after validating the file in the app. Each pet should face +Z, stand on Y=0, and fit within roughly 2 world units in height. Tune `scale`, `camera` and `target` in the manifest per species. Use sculpted, authored silhouettes, expressive eyes and face, proper UVs and textures. The app does not construct animal shapes from Three.js primitives.

## Rig and animation contract

- Supply a skinned rig with authored clips `Idle`, `Blink`, `Breathing`, `Wave`, `Happy`, `Excited`, `Talk`, `Listen`, `Thinking`, `Sleepy`, `Sleep`, `Sad`, `Playful`, `Jump`, `Sit`. Clip names can be remapped in `config.ts`; missing clips fall back to `Idle`.
- Keep head and eyes responsive. A node named `Head` (or `Head_CTRL`) enables subtle cursor following. Face meshes may expose morph targets `Blink`, `Smile`, `MouthOpen`, `Sad`; these enhance clip animation and are optional. Authored variants may expose `BodyCompact`, `BodyTall`, `EarPointed`, `EarFloppy`, `EarLong`, `TailFluffy`, `TailShort`. Without those morphs, the corresponding controls remain saved but cannot change the mesh shape.
- Name recolorable materials `fur_primary`, `fur_secondary`, `eye_iris`. Other authored material and texture detail is preserved. The renderer clones materials per pet before tinting them.
- Wearable anchor nodes can be named `Head`, `NeckAttach`, `EyesAttach`, `BodyAttach`. Item GLBs live under `items/` with the names in `config.ts`. Set an item's `ready` flag only when its GLB fits the anchor and species. Clothing should be authored to fit the species rig; rigid attachments alone are insufficient for complex garments.

## Export and performance

Export GLB with embedded PBR textures, sensible texture sizes and compressed geometry/textures where practical. Validate desktop and mobile GPU use, all clips, material colors and accessory fit before marking an asset ready. The renderer limits device pixel ratio, pauses when off screen, offers a lower quality mode, and uses reduced motion preferences. Supply license and attribution details with each delivered art package.
