# Bundled pet models

The app includes a free stylized GLB for each of the seven pet species. Files are served locally from each species directory, so runtime rendering does not depend on an external model host. The models differ in visual style and animation coverage; they are a usable free asset set, not a matched premium art collection.

| Species | Asset | License | Animation |
| --- | --- | --- | --- |
| Cat | [Quaternius Cat on Poly Pizza](https://poly.pizza/m/qKICY6xla2) | CC0 | 8 clips |
| Dog | [Quaternius Shiba Inu, Ultimate Animated Animal Pack](https://quaternius.com/packs/ultimateanimatedanimals.html) | CC0 | 12 clips |
| Fox | [Quaternius Fox, Ultimate Animated Animal Pack](https://quaternius.com/packs/ultimateanimatedanimals.html) | CC0 | 12 clips |
| Rabbit | [Quaternius Bunny on Poly Pizza](https://poly.pizza/m/irZjWFARyl) | CC0 | 14 clips |
| Panda | [Quaternius Panda on Poly Pizza](https://poly.pizza/m/q1uJ28Hs8T) | CC0 | 30 clips |
| Bear | [Bear by jiang liu on Poly Pizza](https://poly.pizza/m/3Eb9oLfZYIc) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) | Static; the app adds gentle whole-model motion |
| Wolf | [Quaternius Wolf, Ultimate Animated Animal Pack](https://quaternius.com/packs/ultimateanimatedanimals.html) | CC0 | 12 clips |

The dog, fox, and wolf source glTFs were repackaged as self-contained GLBs by `tools/pack_pet_gltf.py`; no model geometry was generated. The bear model is credited in the pet scene as required by its license. `tools/inspect_pet_assets.py` validates the binary GLBs and reports mesh, skin, and clip metadata.

The six animated models are rigged. Clip names and scales are mapped in `frontend/src/features/pet/config.ts`. The bear has no rig or authored clips. The free assets have no consistent recolorable material slots, facial morphs, or wearable attachment points. The appearance form can save those choices, but color, ears, tail, markings, and clothing do not change these particular meshes. Body style applies a small overall scale change. Wearable files have not been supplied; their `ready` flags remain false. The panda has a built-in outfit and the rabbit has a built-in carrot.

To replace an asset, put a compatible `companion.glb` in the species directory and tune `scale`, `offset`, `camera`, `target`, and clip mappings in `config.ts`. For full customization, name recolorable materials `fur_primary`, `fur_secondary`, and `eye_iris`; add appropriate morph targets and clothing anchors. Keep source and license information here for every replacement.
