# BioCV Scene Importer for Blender

![License](https://img.shields.io/badge/license-MIT-blue)
![Language](https://img.shields.io/badge/language-Python-informational)
![Version](https://img.shields.io/github/v/release/kapdap/re-cvx-blender?label=version)
![Build](https://img.shields.io/github/actions/workflow/status/kapdap/re-cvx-blender/release.yml?label=build)

A Blender add-on that imports 3D scenes from **Resident Evil: Code: Veronica** room data files.

## Features

- Imports room data, including:
  - Room, actor, object, and item models
  - Actor skeletons, motions, and facial masks
  - Cameras, lights, effect areas, and player spawns
  - Collisions, interactions, triggers, and enemy routes
- Maps TIM2, PVR, and GVR textures
- Automatic PRS detection and decompression
- Supports PlayStation 2, Dreamcast and GameCube files

## Installation

Blender 4.2 or later is required.

### From GitHub

1. Open the [latest GitHub release](https://github.com/kapdap/re-cvx-blender/releases/latest).
2. Under **Assets**, download `add-on-io_scene_biocv-v<version>.zip`.
3. In Blender, install the downloaded ZIP via **Edit > Preferences > Get Extensions > Install from Disk**.

### From source

1. Clone the repository.
2. Build the extension:

```bash
python build.py
```

3. In Blender, install `dist/add-on-io_scene_biocv-v<version>.zip` via **Edit > Preferences > Get Extensions > Install from Disk**.

## Usage

1. In Blender, go to **File > Import > RDX (.rdx/.rdt)**.
2. Select one or more `.rdx`, `.rdt` or `.bin` files.
3. Choose which data to import:
   - Models
     - Room
     - Actors
     - Motions
     - Objects
     - Items
   - Cameras
   - Lights
   - Textures
   - Areas
     - Effects
     - Player
     - Collisions
     - Interactions
     - Triggers
     - Routes
   - Positions
     - Actors
     - Objects
     - Items
4. Click **Import RDX**.

You can also drag and drop `.rdx` or `.rdt` files into the 3D viewport.

## Acknowledgements

- [@fmil95](https://github.com/fmil95) - [recvx-decomp](https://github.com/AshfordFamily/recvx-decomp)
- [@mortician](https://github.com/mortician) - [lib_biocv](https://github.com/mortician/lib_biocv)

## AI disclosure

AI tools are used in the development this project.

## License

[MIT](LICENSE).
