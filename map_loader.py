from ursina import *
import time
import os

def load_map(map_file_path=None):
    """
    Loads the map from server-provided file or assets/map/lesiktest.fbx (preferred) or lesiktest.obj
    Args:
        map_file_path: Optional path to map file received from server
    Returns the map entity, or None if loading fails
    """
    forest_map = None
    
    # If server provided a map file, use it
    if map_file_path and os.path.exists(map_file_path):
        print(f"Loading map from server: {map_file_path}")
        try:
            start_time = time.time()
            # Determine file extension
            ext = os.path.splitext(map_file_path)[1].lower()
            if ext == '.fbx':
                map_model = load_model(map_file_path, use_deepcopy=False)
            elif ext in ['.obj', '.mtl']:
                # For OBJ, try without extension
                base_path = os.path.splitext(map_file_path)[0]
                map_model = load_model(base_path, use_deepcopy=False)
            else:
                map_model = load_model(map_file_path, use_deepcopy=False)
            
            load_time = time.time() - start_time
            print(f"✓ Map model loaded successfully in {load_time:.2f} seconds")
            
            if map_model is None:
                print("Warning: Map model loaded but is None")
                raise Exception("Map model is None")
            
            forest_map = Entity(
                model=map_model,
                scale=0.25,
                position=(0, 0, 0),
                double_sided=True
            )
            print(f"Map entity created at position {forest_map.position}")
            if forest_map:
                forest_map.enabled = True
                print("Map entity enabled")
            return forest_map
        except Exception as e:
            print(f"Error loading server map file: {e}")
            print("Falling back to local map files...")
    
    # Fallback to local map files
    print("Loading map from assets/map...")
    print("Trying FBX format first (better compatibility)...")
    
    # Try FBX first (better compatibility)
    try:
        start_time = time.time()
        print("Attempting to load lesiktest.fbx...")
        map_model = load_model('map/lesiktest.fbx', use_deepcopy=False)
        
        load_time = time.time() - start_time
        print(f"✓ FBX model loaded successfully in {load_time:.2f} seconds")
        
        if map_model is None:
            print("Warning: FBX model loaded but is None")
            raise Exception("FBX model is None")
        
        # Check for materials BEFORE creating entity
        print("Checking for textures and materials...")
        has_materials = False
        
        # Check for materials in the model
        if hasattr(map_model, 'materials') and map_model.materials:
            print(f"Found {len(map_model.materials)} materials in model")
            has_materials = True
            # Try to inspect materials for textures
            for i, mat in enumerate(map_model.materials):
                if hasattr(mat, 'texture') and mat.texture:
                    print(f"  Material {i} has texture: {mat.texture}")
        else:
            print("No materials found in model")
        
        # Create entity with the model
        # Scale is 0.25 (4 times smaller) as requested
        forest_map = Entity(
            model=map_model,
            scale=0.25,  # 4 times smaller
            position=(0, 0, 0),
            double_sided=True
        )
        
        # Note: Collision handling
        # The ground plane in client.py provides basic ground collision
        # For collisions with map objects (trees, buildings, etc.), you would need to:
        # 1. Add individual box colliders for specific important objects
        # 2. Create a low-poly collision mesh in Blender and load it separately
        # 3. Use custom collision detection
        # 
        # Mesh colliders on this large model (598k+ vertices) cause severe lag,
        # so we're not using them here. The ground plane handles basic walking.
        print("Map loaded - using ground plane in client.py for basic collision")
        print("For object collisions, add individual colliders or use a simplified collision mesh")
        
        # Try to load textures from MTL file or texture files
        print("Attempting to load textures...")
        texture_loaded = False
        
        # First, check MTL file for texture references
        try:
            from pathlib import Path
            import re
            mtl_file = Path(application.asset_folder) / 'map' / 'lesiktest.mtl'
            if mtl_file.exists():
                print("Parsing MTL file for texture references...")
                with open(mtl_file, 'r') as f:
                    mtl_content = f.read()
                    
                    # Look for map_Kd (texture file references)
                    texture_refs = re.findall(r'map_Kd\s+(.+)', mtl_content)
                    if texture_refs:
                        print(f"Found {len(texture_refs)} texture references in MTL")
                        # Try to load the first texture
                        for tex_ref in texture_refs:
                            tex_ref = tex_ref.strip()
                            # Try different possible paths
                            possible_paths = [
                                f'map/{tex_ref}',
                                f'map/textures/{tex_ref}',
                                tex_ref
                            ]
                            for tex_path in possible_paths:
                                try:
                                    forest_map.texture = tex_path
                                    print(f"✓ Applied texture: {tex_path}")
                                    texture_loaded = True
                                    break
                                except:
                                    continue
                            if texture_loaded:
                                break
                    
                    # If no textures found, try to apply colors from materials
                    if not texture_loaded:
                        print("No texture files found in MTL, trying to apply material colors...")
                        # Don't apply a single color - let the model use its default appearance
                        # The gray appearance might be from the model itself
                        print("Model will use its default appearance")
        except Exception as mtl_e:
            print(f"Could not parse MTL file: {mtl_e}")
        
        # If still no texture, try to find texture files in folders
        if not texture_loaded:
            try:
                from pathlib import Path
                map_folder = Path(application.asset_folder) / 'map'
                # Check multiple possible locations
                search_folders = [map_folder, map_folder / 'textures', map_folder.parent]
                texture_files = []
                for folder in search_folders:
                    if folder.exists():
                        texture_files.extend(list(folder.glob('*.png')) + 
                                            list(folder.glob('*.jpg')) + 
                                            list(folder.glob('*.jpeg')))
                
                if texture_files:
                    print(f"Found {len(texture_files)} texture files, attempting to apply...")
                    for tex_file in texture_files[:3]:  # Try first 3 textures
                        try:
                            rel_path = tex_file.relative_to(Path(application.asset_folder))
                            texture_path = str(rel_path).replace('\\', '/')
                            forest_map.texture = texture_path
                            print(f"✓ Applied texture: {texture_path}")
                            texture_loaded = True
                            break
                        except Exception as e:
                            print(f"  Could not apply {tex_file.name}: {e}")
                            continue
            except Exception as e:
                print(f"Error searching for texture files: {e}")
        
        # Final fallback - don't override with gray, let model show its natural colors
        if not texture_loaded and not has_materials:
            print("No textures found - model will display with default appearance")
            # Don't set color or texture - let the model use whatever it has
        
        # Check if there are texture files in the map folder or subfolders
        try:
            from pathlib import Path
            map_folder = Path(application.asset_folder) / 'map'
            # Check in map folder
            texture_files = list(map_folder.glob('*.png')) + list(map_folder.glob('*.jpg')) + list(map_folder.glob('*.jpeg'))
            # Also check in textures subfolder if it exists
            textures_folder = map_folder / 'textures'
            if textures_folder.exists():
                texture_files.extend(list(textures_folder.glob('*.png')) + list(textures_folder.glob('*.jpg')) + list(textures_folder.glob('*.jpeg')))
            
            if texture_files:
                print(f"Found {len(texture_files)} texture image files: {[f.name for f in texture_files[:5]]}")
                # Try to apply the first texture as a test
                try:
                    # Get relative path for Ursina
                    first_texture = texture_files[0]
                    rel_path = first_texture.relative_to(Path(application.asset_folder))
                    texture_path = str(rel_path).replace('\\', '/')
                    print(f"Attempting to apply texture: {texture_path}")
                    # Note: This might not work if the model has multiple materials
                    # But it's worth trying
                except Exception as tex_e:
                    print(f"Could not apply texture: {tex_e}")
            else:
                print("No texture image files (.png/.jpg) found in map folder")
                print("When using 'Path Mode: Copy' in Blender, textures should be copied to a folder")
                print("Check if Blender created a 'textures' subfolder or copied them elsewhere")
        except Exception as e:
            print(f"Could not check for texture files: {e}")
        
        # Debug: Check model attributes
        print(f"Model attributes: {[attr for attr in dir(map_model) if not attr.startswith('_')][:10]}")
        
        if not has_materials:
            print("\n⚠️  WARNING: Model appears to have no materials/textures")
            print("   Possible issues:")
            print("   1. Textures weren't properly set up in Blender materials")
            print("   2. FBX export didn't include materials/textures")
            print("   3. Try 'Path Mode: Embed' instead of 'Copy' in Blender export")
            print("   4. Make sure materials in Blender have Image Texture nodes connected")
        print(f"Map entity created at position {forest_map.position}")
        
        if forest_map:
            forest_map.enabled = True
            print("Map entity enabled")
        
        return forest_map
        
    except Exception as e_fbx:
        print(f"FBX loading failed: {e_fbx}")
        print("\nFalling back to OBJ format...")
        
        # Fallback to OBJ
        try:
            start_time = time.time()
            map_model = load_model('map/lesiktest', use_deepcopy=False)
            
            load_time = time.time() - start_time
            print(f"✓ OBJ model loaded successfully in {load_time:.2f} seconds")
            
            if map_model is None:
                print("Warning: OBJ model loaded but is None")
                raise Exception("OBJ model is None")
            
            forest_map = Entity(
                model=map_model,
                scale=0.25,  # 4 times smaller
                position=(0, 0, 0),
                # Don't set color as it overrides textures
                double_sided=True
            )
            print(f"Map entity created at position {forest_map.position}")
            
            if forest_map:
                forest_map.enabled = True
                print("Map entity enabled")
            
            return forest_map
            
        except Exception as e_obj:
            error_msg = str(e_obj)
            print(f"\n{'='*60}")
            print("ERROR: Failed to load map file (both FBX and OBJ)")
            print(f"{'='*60}")
            print(f"FBX Error: {e_fbx}")
            print(f"OBJ Error: {error_msg}")
            
            if "triangles:0" in error_msg or "same length" in error_msg:
                print("\nThe OBJ file has format compatibility issues.")
                print("The FBX file should work better - check if it exists in assets/map/")
            
            import traceback
            traceback.print_exc()
            forest_map = None
    
    return forest_map

