from pathlib import Path
from ursina import *
import time
import texture_loader
import path_resolver


def load_map(map_file_path=None):
    """
    Load a map model (prefer server path, otherwise bundled assets) and ensure textures apply.
    """
    preferred = Path(map_file_path) if map_file_path else None
    model_path = resolve_map_model_path(preferred)

    if model_path is None:
        print("WARNING: No map file found. Clients will need map files locally.")
    else:
        print(f"Loading map from {model_path}")

    # Spawn a persistent floor so players never fall through while the map loads.
    floor = Entity(
        model="cube",
        scale=(500, 1, 500),
        position=(0, -5, 0),
        collider="box",
        visible=True,
    )
    
    # Try to apply a texture to the floor from mesto folder
    texture_dir = path_resolver.get_texture_directory(model_path)
    if texture_dir.exists():
        # Try to find an asphalt or ground texture
        for tex_file in texture_dir.glob("RGB_*asphalt*.png"):
            try:
                floor.texture = load_texture(str(tex_file))
                break
            except:
                pass
        # Fallback to any RGB texture
        if not hasattr(floor, 'texture') or floor.texture is None:
            for tex_file in texture_dir.glob("RGB_*.png"):
                try:
                    floor.texture = load_texture(str(tex_file))
                    break
                except:
                    pass

    start_time = time.time()
    try:
        if model_path is None:
            raise RuntimeError("No map model path could be resolved")

        try:
            print(f"Attempting to load model from: {model_path}")
            model = load_model(str(model_path), use_deepcopy=False)
        except Exception as e:
            print(f"First load attempt failed: {e}, trying without use_deepcopy...")
            try:
                model = load_model(str(model_path))
            except Exception as e2:
                print(f"Second load attempt also failed: {e2}")
                raise RuntimeError(f"Failed to load model: {e2}")

        if model is None:
            raise RuntimeError("load_model returned None")

        print(f"Model loaded successfully, type: {type(model)}")

        # Check if this is a GLB file (which has embedded textures)
        is_glb = model_path.suffix.lower() in ['.glb', '.gltf']
        
        # For GLB files, try without collider first (mesh colliders can be problematic with complex GLB geometry)
        if is_glb:
            try:
                forest_map = Entity(
                    model=model,
                    scale=1,
                    position=(0, 1, 0),
                    double_sided=True,
                    collider="mesh",
                )
                print("Forest map entity created successfully (GLB, with mesh collider)")
            except Exception as e:
                print(f"Error creating forest_map entity: {e}")
                raise
        else:
            # For FBX files, try with mesh collider
            try:
                forest_map = Entity(
                    model=model,
                    scale=0.5,
                    position=(0, -1.5, 0),
                    double_sided=True,
                    collider="mesh",
                )
                print("Forest map entity created successfully (FBX, with mesh collider)")
            except Exception as e:
                print(f"Error creating forest_map entity with collider: {e}")
                # Try without collider if mesh collider fails
                try:
                    forest_map = Entity(
                        model=model,
                        scale=0.5,
                        position=(0, -1.5, 0),
                        double_sided=True,
                    )
                    print("Forest map entity created without collider")
                except Exception as e2:
                    print(f"Error creating forest_map entity without collider: {e2}")
                    raise
        
        # Debug: Check model structure
        if hasattr(forest_map, 'children'):
            print(f"Forest map has {len(forest_map.children)} children after creation")
        
        if is_glb:
            print("GLB/GLTF file detected - textures should be embedded in the file")
            # GLB files typically have textures embedded, so we don't need to apply external textures
            # The model should load with its textures automatically
            print("Model loaded with embedded textures from GLB file")
        else:
            # For FBX files, load and apply external textures
            texture_dir = path_resolver.get_texture_directory(model_path)
            print(f"Loading textures from: {texture_dir}")
            textures = texture_loader.load_all_rgb_textures(texture_dir)
            
            if textures:
                print(f"Found {len(textures)} textures, applying to model...")
                
                # Try to access model's materials/parts if available
                rgb_textures_list = [(name, tex) for name, tex in textures.items() if name.startswith("RGB_")]
                if not rgb_textures_list:
                    rgb_textures_list = list(textures.items())
                
                # Check if model has multiple materials or parts
                if hasattr(model, 'materials') and model.materials:
                    print(f"Model has {len(model.materials)} materials")
                    for i, material in enumerate(model.materials):
                        if i < len(rgb_textures_list):
                            tex_name, texture = rgb_textures_list[i % len(rgb_textures_list)]
                            try:
                                material.texture = texture
                                print(f"Applied texture {tex_name} to material {i}")
                            except Exception as e:
                                print(f"Could not apply texture to material {i}: {e}")
                
                # Also try to apply textures to child entities
                texture_index = [0]  # Use list to allow modification in recursive calls
                used_textures = set()
                applied = texture_loader.apply_textures_to_entity(forest_map, textures, texture_dir, texture_index, used_textures)
                
                # If model has sub-meshes or parts, try to access them
                if hasattr(forest_map.model, 'getNumGeoms'):
                    try:
                        num_geoms = forest_map.model.getNumGeoms()
                        print(f"Model has {num_geoms} geometries")
                        for i in range(num_geoms):
                            if i < len(rgb_textures_list):
                                tex_name, texture = rgb_textures_list[i % len(rgb_textures_list)]
                                # Try to create child entity for each geometry
                                try:
                                    child_entity = Entity(
                                        parent=forest_map,
                                        model=forest_map.model,
                                        texture=texture,
                                        double_sided=True
                                    )
                                    print(f"Created child entity with texture {tex_name}")
                                except Exception as e:
                                    print(f"Could not create child entity: {e}")
                    except Exception as e:
                        print(f"Could not access model geometries: {e}")
                
                print(f"Applied textures to {applied} entity/entities")
            else:
                print("WARNING: No RGB textures found in texture directory")

        try:
            forest_map.enabled = True
            forest_map.visible = True
            print("Forest map enabled and made visible")
        except Exception as e:
            print(f"Warning: Could not set enabled/visible: {e}")

        load_time = time.time() - start_time
        print(f"✓ Map loaded in {load_time:.2f}s from {model_path}")
        return forest_map
    except Exception as exc:  # noqa: BLE001
        import traceback
        print(f"Failed to load map: {exc}")
        print("Full traceback:")
        traceback.print_exc()
        print("Returning fallback plane entity...")
        try:
            return Entity(
                model="plane",
                scale=100,
                position=(0, 0, 0),
                color=color.gray,
                collider="box",
            )
        except Exception as e2:
            print(f"Even fallback entity creation failed: {e2}")
            return None
