#!/usr/bin/env python3
"""
Ursina app that loads your FBX map and ensures there's a usable floor/collider so the player
doesn't fall through. It will add a large invisible fallback floor under the map if the map
doesn't provide a walkable floor. Press F2 to toggle collider debug and F3 to toggle the
fallback floor visibility (for debugging).

Place this script next to your assets/ folder:
- ./main.py
- ./assets/map/mestou/model/model.fbx
- ./assets/map/mesto/...(textures)

Run:
    python main.py
"""
import os
from pathlib import Path
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# --- configuration: update if your paths differ ---
MODEL_PATH = Path("assets/map/mestou/model/model.fbx")
TEXTURE_DIR = Path("assets/map/mesto")
# fallback floor parameters
FLOOR_SIZE = (500, 1, 500)   # large flat collider
FLOOR_OFFSET = -1.0          # how far below the map's origin the fallback floor will sit
# -------------------------------------------------

# Make sure relative texture paths inside FBX resolve
script_root = Path(__file__).resolve().parent
os.chdir(script_root)

app = Ursina()

window.color = color.rgb(120, 180, 255)
DirectionalLight(y=2, z=3, shadows=True, rotation=(45, -30, 45))
AmbientLight(color=color.rgba(120, 120, 120, 0.25))

# load model
if not MODEL_PATH.exists():
    print(f"[ERROR] Model not found at {MODEL_PATH}. Using placeholder plane.")
    map_entity = Entity(model='plane', scale=10, color=color.light_gray, collider='box')
else:
    map_entity = Entity(
        model=str(MODEL_PATH),
        collider='mesh',      # use mesh collider for accurate collisions (if the model has geometry)
        double_sided=True,
        scale=1,
        position=(0, 0, 0),
        receive_shadows=True,
    )

# simple recursive walker (Entity.walk() may not exist in all Ursina versions)
def walk_entity(entity: Entity):
    yield entity
    for child in getattr(entity, 'children', []) or []:
        yield from walk_entity(child)

# texture application helper (best-effort)
def apply_textures_from_dir(entity: Entity, texture_dir: Path):
    if not texture_dir.exists():
        return False
    imgs = list(texture_dir.glob("**/*.png")) + list(texture_dir.glob("**/*.jpg")) + list(texture_dir.glob("**/*.jpeg"))
    if not imgs:
        return False
    textures = {}
    for img in imgs:
        try:
            textures[img.stem.lower()] = load_texture(str(img))
        except Exception as e:
            print(f"[WARN] Failed to load texture {img}: {e}")
    if not textures:
        return False

    applied_any = False
    for child in walk_entity(entity):
        child_name = (getattr(child, 'name', '') or '').lower()
        if not child_name:
            continue
        for tex_name, tex in textures.items():
            if tex_name in child_name:
                try:
                    child.texture = tex
                    applied_any = True
                    break
                except Exception as e:
                    print(f"[WARN] Could not apply texture to {child_name}: {e}")

    if not applied_any:
        # fallback: apply the first texture to entire entity
        first_tex = next(iter(textures.values()))
        try:
            entity.texture = first_tex
            applied_any = True
        except Exception as e:
            print(f"[WARN] Fallback texture application failed: {e}")
            applied_any = False

    return applied_any

if MODEL_PATH.exists():
    applied = apply_textures_from_dir(map_entity, TEXTURE_DIR)
    if applied:
        print(f"[INFO] Applied textures from {TEXTURE_DIR}")
    else:
        print(f"[WARN] No textures applied from {TEXTURE_DIR} (FBX may reference other paths).")

# Create the player and put them above the map/floor so they don't immediately fall.
player = FirstPersonController()
player.cursor.visible = False
player.gravity = 1.2
player.speed = 4
player.jump_height = 1.6

# Determine a reasonable spawn Y for the player:
# - If the map has collision (mesh collider), raycast down from above the map origin to find a surface.
# - Otherwise, use a fallback position above the map origin or a global default.
def find_map_surface_y(entity: Entity, sample_x=0, sample_z=0, start_y=50, max_distance=200):
    """
    Raycast downward to find a collision with the map entity.
    Returns the world y coordinate of the hit or None if no hit.
    """
    origin = Vec3(sample_x, start_y, sample_z)
    hit = raycast(origin, direction=Vec3(0, -1, 0), distance=max_distance, ignore=(player,))
    # Ensure we hit the map entity (or a child) by checking the hit entity's ancestry
    if hit.hit:
        # Sometimes raycast returns collisions with other scene objects; accept any hit for spawn
        return hit.world_point.y
    return None

spawn_y = None
if MODEL_PATH.exists():
    # attempt to raycast at map origin
    spawn_y = find_map_surface_y(map_entity, sample_x=map_entity.x, sample_z=map_entity.z)
if spawn_y is None:
    # fallback: try above 0
    spawn_y = 2.0

# Place player slightly above detected surface so they don't spawn intersecting geometry
player.position = Vec3(0, spawn_y + 1.0, 0)

# If the map didn't provide a usable floor (raycast failed), add a large invisible floor collider.
fallback_floor = None
if MODEL_PATH.exists():
    # check if raycast from above player's x,z hits anything (map mesh collider)
    hit_y = find_map_surface_y(map_entity, sample_x=player.x, sample_z=player.z)
    if hit_y is None:
        # no collision detected at player's position -> add fallback floor placed relative to the map origin
        floor_y = map_entity.y + FLOOR_OFFSET
        fallback_floor = Entity(
            model='cube',
            scale=FLOOR_SIZE,
            position=(map_entity.x, floor_y, map_entity.z),
            collider='box',
            color=color.azure,   # visible for debug; we'll hide it immediately
            visible=False
        )
        print(f"[INFO] No floor detected under map; added fallback floor at y={floor_y}")
else:
    # If there's no map at all, add a default floor at y = -1
    fallback_floor = Entity(
        model='cube',
        scale=FLOOR_SIZE,
        position=(0, -1, 0),
        collider='box',
        color=color.azure,
        visible=False
    )
    print("[INFO] Using default fallback floor at y=-1")

# Allow toggling fallback floor visibility for debugging (F3)
def toggle_floor_visual(show: bool):
    if fallback_floor:
        fallback_floor.visible = show

show_colliders = False
def input(key):
    global show_colliders
    if key == 'f2':
        show_colliders = not show_colliders
        from ursina.debug import draw_collider
        if show_colliders:
            print('[DEBUG] Showing colliders (press F2 to hide)')
            # draw collider for map and fallback floor if present
            draw_collider(map_entity, color=color.red)
            if fallback_floor:
                draw_collider(fallback_floor, color=color.yellow)
        else:
            print('[DEBUG] Hiding colliders - restart to fully clear debug visuals')
    if key == 'f3':
        if fallback_floor:
            fallback_floor.visible = not fallback_floor.visible
            print(f"[DEBUG] Fallback floor visible: {fallback_floor.visible}")

help_text = Text(
    text="WASD to move, mouse to look, Space to jump\nF2 toggles collider debug, F3 toggles fallback floor\nClose window or press ESC to quit",
    position=(-0.7, 0.45),
    origin=(0, 0),
    scale=1,
    background=True
)

app.run()