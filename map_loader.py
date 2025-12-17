from pathlib import Path
from ursina import *
from path_resolver import resolve_map_model_path


def load_map(map_file_path=None):
    """
    Load map model with combined colliders.

    - Preferuje cestu, ktorú poslal server (`map_file_path`),
      inak použije lokálnu zabalenú mapu podľa `resolve_map_model_path`.
    - Vždy vytvorí pevný floor s collider=\"box\", aby hráč nespadol.
    - Na samotnú mapu dá collider=\"mesh\", aby mali budovy kolíziu.
    """
    preferred = Path(map_file_path) if map_file_path else None
    model_path = resolve_map_model_path(preferred)

    # Veľký bezpečnostný floor (fyzika pod celou mapou, aj keď odídeš ďaleko)
    floor = Entity(
        model="cube",
        scale=(5000, 5, 5000),   # výrazne väčší ako mapa
        position=(0, -1, 0),     # o niečo nižšie pod mapou
        collider="box",
        color=color.dark_gray,
        visible=False,
    )

    if model_path is None:
        print("WARNING: No map file found.")
        return floor

    try:
        print(f"Loading map from {model_path}")
        model = load_model(str(model_path))
        if not model:
            raise RuntimeError("load_model returned None")

        # Vizuálna mapa + mesh collider pre budovy/steny
        forest_map = Entity(
            model=model,
            scale=1,
            position=(0, 0, 0),
            double_sided=False,  # vypneme double_sided kvôli výkonu
            collider="mesh",      # budovy/steny majú kolíziu podľa geometrie
        )

        # Floor necháme existovať s box colliderom ako „neviditeľnú“ podlahu.
        # Ak ti prekáža vizuálne, môžeš dať: floor.visible = False

        print("✓ Map loaded successfully (mesh collider + box floor)")
        return forest_map

    except Exception as e:
        print("Map load failed:", e)
        return floor
