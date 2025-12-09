from pathlib import Path


def get_asset_root():
    """Get the root asset directory."""
    from ursina import application
    if hasattr(application, 'asset_folder'):
        return Path(application.asset_folder)
    return Path.cwd()


def get_texture_directory(model_path: Path = None):
    """
    Get the texture directory for the model.
    Always uses assets/map/mesto for textures (even if model is in temp directory from server).
    """
    asset_root = get_asset_root()
    texture_dir = asset_root / "map" / "mesto"
    
    # If that doesn't exist, try relative to current directory
    if not texture_dir.exists():
        texture_dir = Path.cwd() / "assets" / "map" / "mesto"
    
    # If still doesn't exist, try relative to script location
    if not texture_dir.exists():
        texture_dir = Path(__file__).resolve().parent / "assets" / "map" / "mesto"
    
    # Last resort: try the model's directory if provided
    if not texture_dir.exists() and model_path and model_path.parent.exists():
        texture_dir = model_path.parent
    
    return texture_dir


def resolve_map_model_path(preferred: Path = None) -> Path | None:
    """
    Pick the first existing map model file.

    The old version only looked for two hard‑coded files. This version:
    - Accepts an explicit file path (with or without extension)
    - Searches common asset roots and all map files in those folders
    - Prefers GLB/GLTF (embedded textures) before FBX
    """
    # Prefer FBX first (per request), then GLB/GLTF.
    ext_priority = (".fbx", ".FBX", ".glb", ".gltf")

    def _maybe_add(path: Path, bag: list[Path], seen: set[Path]):
        if path in seen:
            return
        seen.add(path)
        bag.append(path)

    def _variants(base: Path) -> list[Path]:
        """Generate candidate paths for a base path (with or without suffix)."""
        if base.suffix:  # If caller already provided an extension, try it first
            ordered_exts = (base.suffix,) + tuple(e for e in ext_priority if e != base.suffix)
        else:
            ordered_exts = ext_priority
        return [base.with_suffix(ext) for ext in ordered_exts]

    candidates: list[Path] = []
    seen: set[Path] = set()

    # 1) Caller-provided path (often from server)
    if preferred:
        for p in _variants(preferred.expanduser()):
            _maybe_add(p, candidates, seen)

    asset_root = get_asset_root()

    # 2) Known filenames we ship with (model first, then Untitled)
    hardcoded_bases = [
        asset_root / "map" / "mesto" / "model",
        asset_root / "map" / "mesto" / "Untitled",
        Path.cwd() / "assets" / "map" / "mesto" / "model",
        Path.cwd() / "assets" / "map" / "mesto" / "Untitled",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto" / "model",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto" / "Untitled",
    ]
    for base in hardcoded_bases:
        for p in _variants(base):
            _maybe_add(p, candidates, seen)

    # 3) Any map file in common map directories (useful for newly added maps like lesiktest.fbx)
    search_roots = [
        asset_root / "map",
        asset_root / "map" / "mesto",
        Path.cwd() / "assets" / "map",
        Path.cwd() / "assets" / "map" / "mesto",
        Path(__file__).resolve().parent / "assets" / "map",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for ext in ext_priority:
            for p in root.glob(f"*{ext}"):
                _maybe_add(p, candidates, seen)

    # 4) Return the first existing file following the priority order above
    for path in candidates:
        if path.exists():
            return path

    print("Map file not found. Paths tried:")
    for path in candidates:
        print(f"  - {path}")
    return None


def get_map_paths():
    """
    Get list of all possible map file paths to check.
    Returns list of Path objects in priority order.
    """
    asset_root = get_asset_root()
    paths = []
    
    # Standard locations
    paths.extend([
        asset_root / "map" / "mesto" / "Untitled.glb",
        asset_root / "map" / "mesto" / "Untitled.GLB",
        asset_root / "map" / "mesto" / "model.fbx",
        asset_root / "map" / "mesto" / "model.FBX",
    ])
    
    # Fallback locations
    paths.extend([
        Path.cwd() / "assets" / "map" / "mesto" / "Untitled.glb",
        Path.cwd() / "assets" / "map" / "mesto" / "model.fbx",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto" / "Untitled.glb",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto" / "model.fbx",
    ])
    
    return paths


def get_texture_paths(texture_dir: Path = None):
    """
    Get list of all texture file paths in the texture directory.
    Returns list of Path objects for all supported texture formats.
    """
    if texture_dir is None:
        texture_dir = get_texture_directory()
    
    if not texture_dir.exists():
        return []
    
    texture_paths = []
    texture_extensions = ["*.png", "*.PNG", "*.jpg", "*.JPG", "*.jpeg", "*.JPEG", "*.tga", "*.TGA"]
    
    # Find all texture files with supported extensions
    for ext in texture_extensions:
        for tex_file in texture_dir.glob(ext):
            if tex_file not in texture_paths:
                texture_paths.append(tex_file)
    
    return texture_paths
