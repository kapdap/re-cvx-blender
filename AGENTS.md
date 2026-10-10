# AGENTS.md

Agent guidelines for "BioCV Scene Importer" development, a Blender add-on that imports 3D scenes
from **Resident Evil: Code: Veronica** room data files.

## Development

- Never write migration code or legacy fallbacks when refactoring.
- Write tests only when explicitly asked.

## Building

- Run `python build.py` to create `dist/add-on-io_scene_biocv-v<version>.zip`.

## References

Use these sources as external references to discover the internal game logic and data structures.
Prefer local sources; consult the remote repositories only if the data is not available locally.

### recvx-decomp

A complete decompilation of the game engine source code.

- Local: `./.ref/src`
- Remote: <https://github.com/AshfordFamily/recvx-decomp>

### RDXplorer

RDT/RDX file parser and viewer.

- Local: `./.ref/rdx`
- Remote: <https://github.com/kapdap/re-cvx-tools/tree/master/RDXplorer>
