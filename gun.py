from ursina import *

from enemy import Enemy
import player as player_mod
import json
import time

# ------------------------------
# GLOBALS
# ------------------------------
player = None
gun = None

# Default gun transform (used as base position/rotation for the scene.gltf model)
GUN_POS = Vec3(0.5, -0.5, 1)
GUN_ROT = Vec3(0, 0, 0)
GUN_SCALE = 0.5

# Shooting state
shooting = False
fire_rate = 0.1  # Time between shots (in seconds)
last_shot_time = 0  # Track when last shot was fired

# Damage message throttling - prevent spam to server
last_damage_time = {}  # target_id -> last time damage was sent
damage_cooldown = 0.1  # Minimum time between damage messages to same target (seconds)

# ------------------------------
# SETUP GUN
# ------------------------------
def setup_gun(player_entity, pos=None, rot=None, scale=None):
    """
    Attach the gun to the camera.
    Optional pos, rot, scale override defaults.
    """
    global player, gun, GUN_POS, GUN_ROT, GUN_SCALE
    player = player_entity

    if pos: GUN_POS = Vec3(pos)
    if rot: GUN_ROT = Vec3(rot)
    if scale: GUN_SCALE = scale

    # Gun entity - use the scene.gltf model directly so it keeps its own textures/materials
    gun = Entity(
        parent=camera,
        model='assets/scene.gltf',
        position=GUN_POS,
        rotation=GUN_ROT,
        scale=GUN_SCALE,
        color=None,           # None -> use model's own materials/textures
        collider=None,
        double_sided=True,
        render_queue=1,       # draw after world to avoid clipping into walls
        always_on_top=True,   # keep visible even when close to geometry
    )


# ------------------------------
# GUN SWAY
# ------------------------------
def sway():
    """Simple gun sway based on mouse velocity."""
    if not gun:
        return
    # Base position (.5, -.5) plus a small offset from mouse movement
    gun.x = 0.5 + mouse.velocity[0] * 2
    gun.y = -0.5 + mouse.velocity[1] * 2

# ------------------------------
# SHOOTING
# ------------------------------
def shoot():
    # Check if we can shoot
    if not shooting:
        return
    if not player:
        return
    
    # Build ignore list - only ignore what we absolutely must
    ignore = []
    
    # Always ignore local player
    if player:
        ignore.append(player)
    
    # Ignore gun
    if gun:
        ignore.append(gun)
    
    # Ignore player model (first person model attached to controller)
    if player and hasattr(player, 'playermodel') and player.playermodel:
        ignore.append(player.playermodel)
    
    # Ignore all Text entities (labels) - we want to hit the actual entities, not labels
    # Cache this to avoid scanning every frame - update only when needed
    try:
        from ursina import scene
        # Only scan Text entities if scene is small or cache is invalid
        # For performance, limit to first 100 entities to avoid lag
        entities_list = list(scene.entities)[:100] if hasattr(scene, 'entities') else []
        for ent in entities_list:
            if isinstance(ent, Text):
                if ent not in ignore:
                    ignore.append(ent)
    except:
        pass
    
    # Perform raycast from camera position
    hit_info = raycast(camera.world_position, camera.forward, distance=200, ignore=ignore)
    
    if hit_info.hit:
        target = hit_info.entity
        damage_amount = 20
        
        # For GLB models, the raycast might hit a child mesh instead of the parent entity
        # Walk up the parent chain to find the actual player entity with player_id
        original_target = target
        checked_entities = []
        while target is not None and target not in checked_entities:
            checked_entities.append(target)
            # Check if this entity is a player target
            if getattr(target, 'is_player_target', False) or hasattr(target, 'player_id'):
                break
            # Try to find parent
            if hasattr(target, 'parent') and target.parent:
                target = target.parent
            else:
                break
        
        # If we didn't find a player entity in the parent chain, use the original hit entity
        if not getattr(target, 'is_player_target', False) and not hasattr(target, 'player_id'):
            target = original_target
        
        # Check if target is a player target (marked with is_player_target flag)
        is_player_target = getattr(target, 'is_player_target', False)
        has_player_id = hasattr(target, 'player_id')
        
        if isinstance(target, Enemy):
            # Enemy entity - use enemy's damage method
            target.take_damage(damage_amount)
        elif is_player_target or has_player_id:
            # Player entity (remote player) - send damage to server
            target_pid = getattr(target, 'player_id', None)
            if target_pid:
                target_pid = str(target_pid)
                # Throttle damage messages to prevent spam
                current_time = time.time()
                last_time = last_damage_time.get(target_pid, 0)
                
                if current_time - last_time >= damage_cooldown:
                    # Send damage to server for authoritative handling
                    try:
                        import client
                        if client.sock and client.my_id:
                            damage_msg = {
                                "type": "damage",
                                "target_id": target_pid,
                                "amount": damage_amount
                            }
                            client.sock.sendall(json.dumps(damage_msg).encode() + b"\n")
                            last_damage_time[target_pid] = current_time
                            # Only print occasionally to reduce console spam
                            # print(f"💥 Hit player {target_pid} for {damage_amount} damage")
                    except Exception as e:
                        print(f"Error sending damage to server: {e}")
            else:
                # Local static player model or test target - apply damage directly
                if not hasattr(target, 'health'):
                    player_mod._attach_health(target, max_health=100)
            player_mod.apply_player_damage(target, damage_amount)

def shooting_loop():
    """This function is called once when mouse button is pressed, but actual shooting is handled in update()"""
    # Just ensure shooting flag is set - actual shooting happens in update() loop
    pass

# Reload function removed - no ammo system

# ------------------------------
# HOVER DAMAGE (for debug enemies)
# ------------------------------
def hover_damage():
    if not player or not shooting:
        return
    # Build ignore list - include player, gun, and playermodel if it exists
    ignore = [player, gun] if gun else [player]
    if player and hasattr(player, 'playermodel') and player.playermodel:
        if player.playermodel not in ignore:
            ignore.append(player.playermodel)
    hit_info = raycast(camera.world_position, camera.forward, distance=50, ignore=ignore)
    if not hit_info.hit:
        return

    target = hit_info.entity
    if isinstance(target, Enemy):
        target.take_damage(20)
    else:
        player_mod.apply_player_damage(target, 10)

# ------------------------------
# INPUT HANDLING
# ------------------------------
def handle_input(key):
    global shooting, last_shot_time
    if key == 'left mouse down':
        shooting = True
        # Reset last shot time so first shot happens immediately
        last_shot_time = 0
    elif key == 'left mouse up':
        shooting = False

# ------------------------------
# UPDATE LOOP
# ------------------------------
def update():
    """Handle gun sway and continuous shooting in update loop."""
    global last_shot_time

    # Always apply sway so the gun feels responsive even when not shooting
    sway()

    if not shooting or not player:
        return

    # Check if enough time has passed since last shot
    current_time = time.time()
    if current_time - last_shot_time >= fire_rate:
        shoot()
        last_shot_time = current_time
