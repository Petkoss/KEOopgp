from pathlib import Path
from ursina import *
import path_resolver


def load_all_textures(texture_dir: Path = None):
    """Load all texture files (PNG, JPG, JPEG, TGA, etc.) from the texture directory."""
    if texture_dir is None:
        texture_dir = path_resolver.get_texture_directory()
    
    textures = {}
    if not texture_dir.exists():
        print(f"Texture directory not found: {texture_dir}")
        return textures
    
    # Get all texture paths using path resolver
    texture_paths = path_resolver.get_texture_paths(texture_dir)
    
    # Load each texture
    for tex_file in texture_paths:
        try:
            tex_name = tex_file.stem  # Get filename without extension
            textures[tex_name] = load_texture(str(tex_file))
            print(f"Loaded texture: {tex_name} ({tex_file.suffix})")
        except Exception as e:
            print(f"Failed to load texture {tex_file}: {e}")
    
    print(f"Total textures loaded: {len(textures)}")
    return textures


# Alias for backward compatibility
def load_all_rgb_textures(texture_dir: Path = None):
    """Alias for load_all_textures() for backward compatibility."""
    return load_all_textures(texture_dir)


def apply_textures_to_entity(entity, textures: dict, texture_dir: Path, texture_index=[0], used_textures=set()):
    """Recursively apply textures to entity and all its children, using different textures for each."""
    applied_count = 0
    
    # Get list of RGB textures for cycling
    rgb_textures = [(name, tex) for name, tex in textures.items() if name.startswith("RGB_")]
    if not rgb_textures:
        rgb_textures = list(textures.items())
    
    if not rgb_textures:
        return 0
    
    # Check if entity already has a texture
    has_texture = hasattr(entity, 'texture') and entity.texture is not None
    
    # Try to match texture by entity name first
    if not has_texture and hasattr(entity, 'name') and entity.name:
        entity_name_lower = entity.name.lower()
        best_match = None
        best_score = 0
        
        for tex_name, texture in textures.items():
            tex_name_lower = tex_name.lower()
            score = 0
            # Score based on how well names match
            if entity_name_lower == tex_name_lower:
                score = 100
            elif entity_name_lower in tex_name_lower:
                score = 50
            elif tex_name_lower in entity_name_lower:
                score = 30
            elif any(part in tex_name_lower for part in entity_name_lower.split('_') if len(part) > 3):
                score = 20
            
            if score > best_score:
                best_score = score
                best_match = (tex_name, texture)
        
        if best_match and best_score > 0:
            try:
                entity.texture = best_match[1]
                applied_count += 1
                print(f"Applied texture {best_match[0]} to {entity.name} (score: {best_score})")
                has_texture = True
                used_textures.add(best_match[0])
            except Exception as e:
                print(f"Failed to apply texture {best_match[0]}: {e}")
    
    # If no texture applied yet, cycle through available textures
    if not has_texture:
        # Find next unused texture, or cycle through all
        attempts = 0
        while attempts < len(rgb_textures):
            tex_name, texture = rgb_textures[texture_index[0] % len(rgb_textures)]
            texture_index[0] += 1
            
            # Prefer textures that haven't been used yet
            if tex_name not in used_textures or attempts >= len(rgb_textures) // 2:
                try:
                    entity.texture = texture
                    applied_count += 1
                    entity_name = entity.name if hasattr(entity, 'name') and entity.name else 'entity'
                    print(f"Applied texture {tex_name} to {entity_name}")
                    has_texture = True
                    used_textures.add(tex_name)
                    break
                except Exception as e:
                    print(f"Failed to apply texture {tex_name}: {e}")
            attempts += 1
    
    # Recursively apply to children
    if hasattr(entity, 'children') and entity.children:
        print(f"Entity {getattr(entity, 'name', 'unnamed')} has {len(entity.children)} children")
        for i, child in enumerate(entity.children):
            child_name = getattr(child, 'name', f'child_{i}')
            print(f"  Processing child {i}: {child_name}")
            applied_count += apply_textures_to_entity(child, textures, texture_dir, texture_index, used_textures)
    
    return applied_count
