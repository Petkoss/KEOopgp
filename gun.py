from ursina import *
from enemy import Enemy
import crosshair
import gun_effects

# ------------------------------
# GLOBALS
# ------------------------------
player = gun = muzzle_flash = None
bullet_hole_tex = None
rifle_model = None

# Default gun transform
GUN_POS = Vec3(0.75, -0.8, 1)
GUN_ROT = Vec3(270, 90, 184)
GUN_SCALE = 1.0

# Shooting state
shooting = False
fire_rate = 2  # Slower fire rate (was 0.1)
ammo = 30
max_ammo = 30
reloading = False
reload_time = 1.5
recoil_active = False  # Track if recoil is currently active

# ------------------------------
# LOAD RIFLE MODEL
# ------------------------------
def _try_load_rifle():
    global rifle_model
    for path in ('assets/rifle.glb', 'rifle.glb', 'rifle'):
        try:
            rifle_model = load_model(path)
            return
        except:
            pass

_try_load_rifle()

# ------------------------------
# SETUP GUN
# ------------------------------
def setup_gun(player_entity, pos=None, rot=None, scale=None):
    """
    Attach the gun to the camera.
    Optional pos, rot, scale override defaults.
    """
    global player, gun, muzzle_flash, bullet_hole_tex, GUN_POS, GUN_ROT, GUN_SCALE
    player = player_entity

    if pos: GUN_POS = Vec3(pos)
    if rot: GUN_ROT = Vec3(rot)
    if scale: GUN_SCALE = scale

    # Gun entity
    gun_color = color.gray if not rifle_model else color.white

    gun = Entity(
        parent=camera,
        model=rifle_model or 'cube',
        color=gun_color,
        scale=(0.3, 0.2, 1) if not rifle_model else GUN_SCALE,
        position=GUN_POS,
        rotation=GUN_ROT,
        collider=None,
        double_sided=True,
        render_queue=1,      # draw after world to avoid clipping into walls
        always_on_top=True,  # keep visible even when close to geometry
    )

    # Muzzle flash - positioned at the end of the gun barrel
    # For rifle model, position it forward along the gun's local Z axis
    muzzle_flash = Entity(
        parent=gun,
        model='quad',
        color=color.yellow,
        scale=0.3 * GUN_SCALE,
        position=(0, 0, 0.6),  # Forward along gun barrel
        rotation_x=90,
        enabled=False,
        render_queue=2,
        always_on_top=True,
    )
    
    # Initialize gun effects system
    gun_effects.setup_gun_effects(gun, muzzle_flash, GUN_POS, GUN_ROT, GUN_SCALE)

    # Bullet hole texture
    global bullet_hole_tex
    for path in ('assets/bullet_hole.png', 'bullet_hole', 'white_cube'):
        try:
            bullet_hole_tex = load_texture(path)
            break
        except:
            pass
    
    # Crosshair
    crosshair.setup_crosshair()

# ------------------------------
# TRANSFORM UPDATES (delegated to gun_effects)
# ------------------------------
def set_gun_transform(pos=None, rot=None, scale=None):
    """Update gun transform using gun_effects module."""
    gun_effects.set_gun_transform(pos, rot, scale)

# ------------------------------
# RECOIL & MUZZLE (delegated to gun_effects)
# ------------------------------
def do_recoil():
    """Apply recoil effect using gun_effects module."""
    gun_effects.do_recoil(player)

def do_muzzle_flash():
    """Create muzzle flash effect using gun_effects module."""
    gun_effects.do_muzzle_flash()

# ------------------------------
# BULLET HOLE
# ------------------------------
def create_bullet_hole(hit_info):
    if not hit_info.hit:
        return
    hole = Entity(
        model='quad',
        texture=bullet_hole_tex,
        scale=0.1,
        position=hit_info.world_point + hit_info.world_normal * 0.01,
        billboard=False
    )
    hole.look_at(hit_info.world_point + hit_info.world_normal)
    return hole

# ------------------------------
# SHOOTING
# ------------------------------
def shoot():
    global ammo
    if reloading or ammo <= 0 or not shooting or not mouse.left or not player:
        return
    
    ammo -= 1
    do_recoil()
    do_muzzle_flash()
    
    ignore = [player, gun] if gun else [player]
    hit_info = raycast(camera.world_position, camera.forward, distance=50, ignore=ignore)
    
    if hit_info.hit:
        if isinstance(hit_info.entity, Enemy):
            hit_info.entity.take_damage(20)
        else:
            create_bullet_hole(hit_info)

def shooting_loop():
    if shooting and mouse.left and not reloading:
        shoot()
        invoke(shooting_loop, delay=fire_rate)

def reload():
    global ammo, reloading
    if reloading or ammo == max_ammo:
        return
    
    reloading = True
    if gun:
        reload_offset = Vec3(0, -0.4 * GUN_SCALE, 0)
        gun.animate_position(GUN_POS + reload_offset, duration=0.2)
        gun.animate_position(GUN_POS + reload_offset, duration=reload_time-0.4, delay=0.2)
        gun.animate_position(GUN_POS, duration=0.2, delay=reload_time-0.2)
        # Update gun effects position after reload animation
        invoke(gun_effects.update_gun_position, GUN_POS, delay=reload_time)
    
    invoke(lambda: (globals().update({'ammo': max_ammo, 'reloading': False})), delay=reload_time)

# ------------------------------
# HOVER DAMAGE (for debug enemies)
# ------------------------------
def hover_damage():
    if not player or not shooting:
        return
    ignore = [player, gun] if gun else [player]
    hit_info = raycast(camera.world_position, camera.forward, distance=50, ignore=ignore)
    if hit_info.hit and isinstance(hit_info.entity, Enemy):
        hit_info.entity.take_damage(20)

# ------------------------------
# INPUT HANDLING
# ------------------------------
def handle_input(key):
    global shooting
    if key == 'left mouse down':
        shooting = True
        shooting_loop()
    elif key == 'left mouse up':
        shooting = False
    elif key == 'r':
        reload()

# ------------------------------
# UPDATE LOOP
# ------------------------------
def update():
    hover_damage()
