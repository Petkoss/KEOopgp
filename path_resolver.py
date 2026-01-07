from pathlib import Path


def get_asset_root():
    """Get the root asset directory."""
    from ursina import application
    if hasattr(application, 'asset_folder'):
        return Path(application.asset_folder)
    return Path.cwd()


def get_texture_directory(model_path: Path = None):
    """Get the texture directory for the model."""
    asset_root = get_asset_root()
    texture_dir = asset_root / "map" / "mesto"

    if not texture_dir.exists():
        texture_dir = Path.cwd() / "assets" / "map" / "mesto"

    if not texture_dir.exists():
        texture_dir = Path(__file__).resolve().parent / "assets" / "map" / "mesto"

    if not texture_dir.exists() and model_path and model_path.parent.exists():
        texture_dir = model_path.parent

    return texture_dir


def resolve_map_model_path(preferred: Path = None) -> Path | None:
    """Pick the map model file path.

    Dočasne preferujeme cestu, ktorú pošle server (`preferred`),
    a až potom lokálne zabalené mapy.
    """
    # 1) Najprv skús mapu, ktorú poslal server (temp súbor na klientovi)
    if preferred:
        preferred_path = preferred.expanduser().resolve()
        if preferred_path.exists():
            return preferred_path

    # 2) Potom hľadaj zabalenú mapu v assets
    candidate = (get_asset_root() / "map" / "maleakozeke.glb").resolve()
    if candidate.exists():
        return candidate

    fallback = (Path.cwd() / "assets" / "map" / "maleakozeke.glb").resolve()
    if fallback.exists():
        return fallback

    print("Map file not found. Tried:")
    print(f"  - {candidate}")
    print(f"  - {fallback}")
    if preferred:
        print(f"  - {preferred_path}")
    return None


def get_map_paths():
    """Get list of all possible map file paths to check."""
    asset_root = get_asset_root()
    return [
        asset_root / "map" / "maleakozeke.glb",
        Path.cwd() / "assets" / "map" / "maleakozeke.glb",
        Path(__file__).resolve().parent / "assets" / "map" / "maleakozeke.glb",
    ]


def get_texture_paths(texture_dir: Path = None):
    """Get list of all texture file paths in the texture directory."""
    # External texture loading is disabled for the current GLB-only map.
    return []
