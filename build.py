import argparse
import os
import re
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def src_path(addon):
    return ROOT / "src" / addon


def read_version(src):
    text = (src / "blender_manifest.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        raise RuntimeError("version not found in blender_manifest.toml")
    return m.group(1)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Builds a Blender extension.")
    parser.add_argument(
        "-a",
        "--addon",
        type=str,
        default="io_scene_biocv",
        help="Add-on folder under src/",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output zip path, including filename",
    )
    parser.add_argument(
        "-t",
        "--tag",
        type=str,
        default=None,
        help="Optional tag appended to version (e.g. alpha+timestamp.hash)",
    )
    parser.add_argument(
        "-g",
        "--github",
        action="store_true",
        help="Emit build data to GITHUB_OUTPUT",
    )
    return parser.parse_args(argv)


def validate_sources(src, addon):
    if not src.is_dir():
        sys.exit(f"missing source folder: src/{addon}/")
    if not (src / "blender_manifest.toml").is_file():
        sys.exit(f"missing manifest file: src/{addon}/blender_manifest.toml")


def resolve_output(output, addon, release):
    name = f"add-on-{addon}-v{release}.zip"
    if output is None:
        out_zip = DIST / name
    else:
        out_zip = output.expanduser()
        if not out_zip.is_absolute():
            out_zip = Path.cwd() / out_zip
        if out_zip.is_dir():
            out_zip = out_zip / name
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    return out_zip


def iter_source_files(src):
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
            continue
        yield path


def write_zip(out_zip, src):
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for path in iter_source_files(src):
            z.write(path, path.relative_to(src).as_posix())


def read_changelog(version):
    path = ROOT / "CHANGELOG.md"
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if (m := re.match(r"^## \[?([^\]\s(]+)", line)) and m.group(1) == version
        ),
        None,
    )
    if start is None:
        return ""
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    body = "\n".join(lines[start + 1 : end]).strip()
    m = re.search(r"\(https?://[^)]+\)", lines[start])
    if not m:
        return body
    link = f"**Full Changelog**: {m.group(0)[1:-1]}"
    return f"{body}\n\n{link}" if body else link


def emit_github(outputs):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for key, value in outputs.items():
            delimiter = f"EOF_{uuid.uuid4().hex}"
            f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def main(argv=None):
    args = parse_args(argv)
    src = src_path(args.addon)
    validate_sources(src, args.addon)
    version = read_version(src)
    tag = args.tag or ""
    release = f"{version}-{tag}" if tag else version
    out_zip = resolve_output(args.output, args.addon, version)
    write_zip(out_zip, src)
    print(f"built: {out_zip}")
    if not args.github:
        return
    emit_github(
        {
            "changelog": read_changelog(version),
            "asset_name": out_zip.stem,
            "asset_file": out_zip.name,
            "asset_ext": out_zip.suffix.lstrip("."),
            "asset_path": out_zip.as_posix(),
            "release": release,
            "version": version,
            "tag": tag,
        }
    )


if __name__ == "__main__":
    main()
