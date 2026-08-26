[![License](https://img.shields.io/badge/License-MIT%202.0-blue.svg)](https://opensource.org/license/mit)
[![GitHub release (latest by date)](https://github.com/ppmpreetham/three-blender/releases)]
[![GitHub stars](https://img.shields.io/github/stars/ppmpreetham/three-blender)](https://github.com/ppmpreetham/three-blender/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ppmpreetham/three-blender)](https://github.com/ppmpreetham/three-blender/network/members)
[![GitHub contributors](https://github.com/ppmpreetham/three-blender/graphs/contributors)]

# Three Blender

Write Zero lines of ThreeJS! Now compile your Blender scenes automatically into ThreeJS websites!

Built with 💖 by [Preetham Pemmasani](https://github.com/ppmpreetham)

## Demo

https://github.com/user-attachments/assets/5faaedb7-3adb-446c-af87-2b33b144c3e3

## Installation

- Zip the [`io_three_blender`](./three-blender/io_three_blender) folder (or grab it from the [releases](https://github.com/ppmpreetham/three-blender/releases))
- Open Blender and navigate to `Edit > Preferences > Add-ons > Install`
- Select the zip file
- Enable the addon by checking the box next to `Import-Export: Three-Blender`

Requires Blender 4.2+.

## Usage

- Create and set up your scene in Blender
- Navigate to Output Properties panel
- Find the `Three.js Export` section
- Enter a path where your HTML file should be saved
- Click `Export Scene`
- Serve the output folder with any static server and open it in a browser

## What Gets Exported

| Blender                                                          | Three.js                                                                    |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Perspective / ortho cameras (focal length, clipping, lens shift) | `PerspectiveCamera` / `OrthographicCamera`                                  |
| Sun lamp                                                         | `DirectionalLight` with shadow frustum                                      |
| Point lamp                                                       | `PointLight` with range, decay and soft shadows                             |
| Spot lamp (incl. Track-To constraints)                           | `SpotLight` with cone angle and penumbra                                    |
| Area lamp                                                        | `RectAreaLight`                                                             |
| HDRI world                                                       | Equirect background + image-based lighting (`RGBELoader`)                   |
| World mist                                                       | `THREE.Fog`                                                                 |
| AgX / Filmic / Standard view transform                           | Matching tone mapping + exposure                                            |
| Meshes                                                           | Draco-compressed GLBs; linked duplicates share one download and GPU buffers |
| Procedural shader nodes                                          | Baked into embedded PBR textures (Cycles bake, auto UV if needed)           |
| Shape keys                                                       | glTF morph targets; drive via `model.userData.shapeKeys["Name"](0..1)`      |
| Keyframe animations                                              | Baked GLB clips playing through `AnimationMixer`                            |
| Animated cameras / lamps                                         | Transform tracks baked per frame into `AnimationClip`s                      |
| Compositor Glare + camera DOF (with Post-Processing toggled on)  | `pmndrs/postprocessing` composer: SMAA, `BloomEffect`, `DepthOfFieldEffect`, tone mapping |

## What's Next?

- [ ] Support for Volumetrics
- [ ] Particle systems and hair
- [ ] Procedural texture baking
- [ ] More compositor effects in the post-processing chain (SSAO, motion blur)

## Development

Run the headless smoke test against a real `bpy` build:

```sh
uv venv .venv --python 3.11
uv pip install --python .venv bpy
.venv/python three-blender/test.py  # Windows: .venv\Scripts\python.exe
```

## Contributing

1. Fork the repository.
2. Clone the repository.
3. Create a new branch.
4. Make changes and commit them.
5. Push the changes to your fork.
6. Create a pull request.
7. Make sure to follow the code of conduct.
