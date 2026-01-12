from pathlib import Path
from ursina import *

# Global floor reference to prevent garbage collection
_safety_floor = None


def load_map(map_path: str = None):
    """
    Load map model with combined colliders.

    - Loads map from provided path (defaults to dankomapa.glb)
    - Always creates a large invisible safety floor
    - Map itself uses a mesh collider
    """

    # --- SAFETY FLOOR ------------------------------------------------------
    floor = Entity(
        model="cube",
        scale=(5000, 10, 5000),
        position=(0, -5, 0),      # top at y=0
        collider="box",
        color=color.dark_gray,
        visible=False,
    )

    if floor.collider is None:
        floor.collider = "box"

    if hasattr(floor.collider, "enabled"):
        floor.collider.enabled = True

    global _safety_floor
    _safety_floor = floor

    print("✓ Safety floor created")
    # ----------------------------------------------------------------------

    # --- MAP LOADING -------------------------------------------------------
    # Use default map if no path provided
    if map_path is None:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        map_path = script_dir / "assets" / "map" / "dankomapa.glb"
    
    map_path = Path(map_path)

    if not map_path.exists():
        print(f"❌ Map file not found: {map_path}")
        return floor

    try:
        print(f"Loading map from {map_path}")
        model = load_model(str(map_path))
        if not model:
            raise RuntimeError("load_model returned None")

        forest_map = Entity(
            model=model,
            scale=1,
            position=(0, 0, 0),
            collider="mesh",
            double_sided=False,
            color=color.white,
        )

        # --- FORCE OPAQUE MATERIALS ----------------------------------------
        try:
            from panda3d.core import TransparencyAttrib, Material, Texture, ColorScaleAttrib

            def make_opaque(node):
                if not node:
                    return

                node.setTransparency(TransparencyAttrib.MNone)

                if node.hasGeom():
                    for i in range(node.getNumGeoms()):
                        state = node.getGeomState(i)
                        if not state:
                            continue

                        new_state = state.makeCopy()
                        new_state.setAttrib(
                            TransparencyAttrib.make(TransparencyAttrib.MNone)
                        )
                        new_state.setAttrib(
                            ColorScaleAttrib.make((1, 1, 1, 1))
                        )

                        if state.hasAttrib(Texture.getClassType()):
                            tex_attrib = state.getAttrib(Texture.getClassType())
                            for s in range(tex_attrib.getNumOnStages()):
                                tex = tex_attrib.getOnStage(s)
                                if tex:
                                    try:
                                        tex.setFormat(Texture.F_rgb)
                                    except:
                                        pass

                        if state.hasAttrib(Material.getClassType()):
                            mat = state.getAttrib(Material.getClassType())
                            if mat:
                                new_mat = Material()
                                new_mat.setAmbient(mat.getAmbient())
                                d = mat.getDiffuse()
                                new_mat.setDiffuse((d[0], d[1], d[2], 1))
                                new_mat.setSpecular(mat.getSpecular())
                                new_mat.setEmission(mat.getEmission())
                                new_mat.setShininess(mat.getShininess())
                                new_state.setAttrib(new_mat)

                        node.setGeomState(i, new_state)

                for child in node.getChildren():
                    make_opaque(child)

            # Access nodePath through the entity's render property (Panda3D NodePath)
            try:
                if hasattr(forest_map, 'render') and forest_map.render:
                    make_opaque(forest_map.render)
                    print("✓ Transparency disabled on map")
                elif hasattr(forest_map, 'model') and hasattr(forest_map.model, 'nodePath') and forest_map.model.nodePath:
                    make_opaque(forest_map.model.nodePath)
                    print("✓ Transparency disabled on map")
            except (AttributeError, TypeError) as e:
                # If nodePath access fails, skip transparency fix (non-critical)
                print(f"Note: Could not apply transparency fix: {e}")

        except Exception as e:
            print("Transparency fix error:", e)
        # ------------------------------------------------------------------

        print("✓ Map loaded successfully")
        return forest_map

    except Exception as e:
        print("❌ Map load failed:", e)
        return floor
