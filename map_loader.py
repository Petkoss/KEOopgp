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
            scale=2,
            position=(0, 0, 0),
            double_sided=False,  # vypneme double_sided kvôli výkonu
            collider="mesh",      # budovy/steny majú kolíziu podľa geometrie
            color=color.white,    # Force white color (no tinting, full opacity)
        )
        
        # Force opaque rendering - disable transparency on all materials and nodes
        try:
            from panda3d.core import TransparencyAttrib, Material, Texture, SamplerState, ColorAttrib, ColorScaleAttrib
            
            # Recursively make all nodes and materials opaque
            def make_opaque(node):
                if not node:
                    return
                
                # Set transparency to none on the node itself
                node.setTransparency(TransparencyAttrib.MNone)
                
                # Get all geometry nodes and modify their states
                if node.hasGeom():
                    for geom_index in range(node.getNumGeoms()):
                        state = node.getGeomState(geom_index)
                        if not state:
                            continue
                        
                        # Create new state with no transparency
                        new_state = state.makeCopy()
                        new_state.setAttrib(TransparencyAttrib.make(TransparencyAttrib.MNone))
                        
                        # Force color scale alpha to 1.0 (fully opaque)
                        # This overrides any alpha in textures or materials
                        new_state.setAttrib(ColorScaleAttrib.make((1, 1, 1, 1)))
                        
                        # Modify textures to ignore alpha channel
                        if state.hasAttrib(Texture.getClassType()):
                            tex_attrib = state.getAttrib(Texture.getClassType())
                            if tex_attrib:
                                # Get all texture stages and modify them
                                for stage in range(tex_attrib.getNumOnStages()):
                                    texture = tex_attrib.getOnStage(stage)
                                    if texture:
                                        try:
                                            # Force texture to RGB format (no alpha)
                                            if texture.getFormat() in [Texture.F_rgba, Texture.F_rgbm, Texture.F_rgba4, Texture.F_rgba8]:
                                                texture.setFormat(Texture.F_rgb)
                                            # Set alpha scale to 1.0
                                            if hasattr(texture, 'setAlphaScale'):
                                                texture.setAlphaScale(1.0)
                                        except Exception as tex_err:
                                            pass
                        
                        # Modify materials to force full opacity
                        if state.hasAttrib(Material.getClassType()):
                            mat = state.getAttrib(Material.getClassType())
                            if mat:
                                # Create new material with full opacity
                                new_mat = Material()
                                new_mat.setAmbient(mat.getAmbient())
                                # Force diffuse alpha to 1.0
                                diffuse = mat.getDiffuse()
                                if len(diffuse) >= 4:
                                    new_mat.setDiffuse((diffuse[0], diffuse[1], diffuse[2], 1.0))
                                else:
                                    new_mat.setDiffuse(mat.getDiffuse())
                                new_mat.setSpecular(mat.getSpecular())
                                new_mat.setEmission(mat.getEmission())
                                new_mat.setShininess(mat.getShininess())
                                new_state.setAttrib(new_mat)
                        
                        node.setGeomState(geom_index, new_state)
                
                # Recursively process children
                for child in node.getChildren():
                    make_opaque(child)
            
            if hasattr(forest_map, 'nodePath') and forest_map.nodePath:
                make_opaque(forest_map.nodePath)
                print("✓ Disabled transparency on map materials and textures")
            else:
                print("Warning: Could not access nodePath to disable transparency")
                    
        except Exception as e:
            print(f"Error setting transparency: {e}")
            import traceback
            traceback.print_exc()

        # Floor necháme existovať s box colliderom ako „neviditeľnú“ podlahu.
        # Ak ti prekáža vizuálne, môžeš dať: floor.visible = False

        print("✓ Map loaded successfully (mesh collider + box floor)")
        return forest_map

    except Exception as e:
        print("Map load failed:", e)
        return floor
