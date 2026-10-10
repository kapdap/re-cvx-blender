# BioCV Scene Importer for Blender

![License](https://img.shields.io/badge/license-MIT-blue)
![Language](https://img.shields.io/badge/language-Python-informational)
![Version](https://img.shields.io/github/v/release/kapdap/re-cvx-blender?label=version)
![Build](https://img.shields.io/github/actions/workflow/status/kapdap/re-cvx-blender/release.yml?label=build)

A Blender add-on that imports 3D scenes from **Resident Evil: Code: Veronica** room data files.

## Features

- Imports room geometry, models, textures and trigger zones
- Maps TIM2, PVR and GVR textures
- Automatic PRS detection and decompression
- Supports PlayStation 2, Dreamcast and GameCube files

## Installation

### From GitHub

1. Open the [latest GitHub release](https://github.com/kapdap/re-cvx-blender/releases/latest).
2. Under **Assets**, download `add-on-io_scene_biocv-v<version>.zip`.
3. In Blender, install the downloaded ZIP via **Edit > Preferences > Get Extensions > Install from Disk**.

### From source

1. Clone the repository.
2. Run the build script.
3. Install the add-on as a Blender extension:

```bash
python build.py
```

This produces `dist/add-on-io_scene_biocv-v<version>.zip`. In Blender, install it via **Edit > Preferences > Get Extensions > Install from Disk**.

## Usage

1. In Blender, go to **File > Import > RDX (.rdx/.rdt)**.
2. Select one or more `.rdx` or `.rdt` files.
3. Choose which data to import:
   - Models
     - Room
     - Actors
     - Objects
     - Items
   - Cameras
   - Lights
   - Textures
4. Click **Import RDX**.

You can also drag and drop `.rdx` / `.rdt` files into the 3D viewport.

## Acknowledgements

- [@fmil95](https://github.com/fmil95) - [recvx-decomp](https://github.com/AshfordFamily/recvx-decomp)
- [@mortician](https://github.com/mortician) - [lib_biocv](https://github.com/mortician/lib_biocv)

## License

[MIT](LICENSE).
