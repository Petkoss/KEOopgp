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
    Choose the first existing map model path from common locations.
    
    Priority order:
    1. Preferred path (if provided)
    2. assets/map/mesto/Untitled.glb (GLB with embedded textures)
    3. assets/map/mesto/model.fbx (FBX file)
    4. Fallback locations
    """
    def _paths_for_base(base: Path):
        """Generate paths with different extensions for a base path."""
        exts = (".fbx", ".FBX", ".gltf", ".glb")
        return [base.with_suffix(ext) for ext in exts]

    candidates: list[Path] = []
    
    # First priority: preferred path (usually from server)
    if preferred:
        candidates.extend(_paths_for_base(preferred.expanduser()))

    asset_root = get_asset_root()
    
    # Second priority: standard locations in assets folder
    bases = [
        asset_root / "map" / "mesto" / "Untitled",  # Untitled.glb (textures embedded)
        asset_root / "map" / "mesto" / "model",  # model.fbx
    ]
    
    # Third priority: fallback locations
    fallback_bases = [
        Path.cwd() / "assets" / "map" / "mesto" / "Untitled",
        Path.cwd() / "assets" / "map" / "mesto" / "model",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto" / "Untitled",
        Path(__file__).resolve().parent / "assets" / "map" / "mesto" / "model",
    ]
    
    # Add all candidate paths
    for base in bases + fallback_bases:
        candidates.extend(_paths_for_base(base))

    # Find first existing path
    for path in candidates:
        if path.exists():
            return path

    # If nothing found, print debug info
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
