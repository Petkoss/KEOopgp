from pathlib import Path
from ursina import *
import time
import os


def _find_texture_for_model(model_path: Path):
    """Return the first diffuse texture referenced in the sibling .mtl file."""
    mtl_path = model_path.with_suffix(".mtl")
    if not mtl_path.exists():
        return None

    try:
        with open(mtl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("map_kd"):
                    tex_ref = line.split(maxsplit=1)[1].strip()
                    texture_path = mtl_path.parent / tex_ref
                    if texture_path.exists():
                        return texture_path
    except Exception as exc:  # noqa: BLE001
        print(f"Could not parse MTL for textures: {exc}")

    return None


def _find_mesto_texture():
    """Pick a diffuse texture from assets/map/mesto/model (or parent) if available."""
    model_dir = Path(application.asset_folder) / "map" / "mesto" / "model"
    base_dir = model_dir.parent
    candidates = [model_dir, base_dir]

    for dir_path in candidates:
        for ext in (".png", ".jpg", ".jpeg"):
            candidate = dir_path / f"model{ext}"
            if candidate.exists():
                return candidate

    for dir_path in candidates:
        for ext in (".png", ".jpg", ".jpeg"):
            for candidate in dir_path.glob(f"*{ext}"):
                return candidate
    return None


def _resolve_map_model_path(preferred: Path | None) -> Path | None:
    """Choose the first existing map model path from common locations."""
    def _paths_for_base(base: Path):
        exts = (".fbx", ".FBX", ".gltf", ".glb")
        return [base.with_suffix(ext) for ext in exts]

    candidates: list[Path] = []
    if preferred:
        candidates.extend(_paths_for_base(preferred.expanduser()))

    asset_root = Path(application.asset_folder)
    bases = [
        asset_root / "map" / "mesto" / "model" / "model",
        asset_root / "map" / "mesto" / "model",
        asset_root / "map" / "mesto" / "model.fbx",  # direct file
        Path.cwd() / "map" / "mesto" / "model" / "model",
        Path(__file__).resolve().parent / "map" / "mesto" / "model" / "model",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto" / "model" / "model",
    ]

    for base in bases:
        candidates.extend(_paths_for_base(base))

    for path in candidates:
        if path.exists():
            return path

    print("Map file not found. Paths tried:")
    for path in candidates:
        print(f"  - {path}")
    return None


def load_map(map_file_path=None):
    """
    Load a map model (prefer server path, otherwise bundled assets) and ensure textures apply.
    """
    preferred = Path(map_file_path) if map_file_path else None
    model_path = _resolve_map_model_path(preferred)

    if model_path is None:
        print("WARNING: No map file found. Clients will need map files locally.")
    else:
        print(f"Loading map from {model_path}")

    # Spawn a persistent floor so players never fall through while the map loads.
    floor = Entity(
        model="cube",
        scale=(500, 1, 500),
        position=(0, 0, 0),
        texture="assets/floor.jpg",
        collider="box",
        visible=True,
    )
    floor_tex = _find_mesto_texture()
    if floor_tex:
        try:
            floor.texture = load_texture(str(floor_tex))
        except Exception:
            pass

    start_time = time.time()
    try:
        if model_path is None:
            raise RuntimeError("No map model path could be resolved")

        try:
            model = load_model(str(model_path), use_deepcopy=False)
        except Exception:
            model = load_model(str(model_path))

        if model is None:
            raise RuntimeError("load_model returned None")

        forest_map = Entity(
            model=model,
            scale=0.025,
            position=(0, -3, 0),
            double_sided=True,
            collider="mesh",
        )

        texture_path = _find_texture_for_model(model_path)
        if not texture_path:
            texture_path = _find_mesto_texture()

        if texture_path:
            try:
                forest_map.texture = load_texture(str(texture_path))
                print(f"Texture applied: {texture_path}")
            except Exception as tex_exc:  # noqa: BLE001
                print(f"Failed to apply texture {texture_path}: {tex_exc}")

        forest_map.enabled = True
        forest_map.visible = True

        load_time = time.time() - start_time
        print(f"✓ Map loaded in {load_time:.2f}s from {model_path}")
        return forest_map
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load map: {exc}")
        return Entity(
            model="plane",
            scale=100,
            position=(0, 0, 0),
            color=color.gray,
            collider="box",
        )
