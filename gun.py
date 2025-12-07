from ursina import *
from enemy import Enemy
import crosshair

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
        collider=None
    )

    # Muzzle flash
    muzzle_flash = Entity(
        parent=gun,
        model='quad',
        color=color.yellow,
        scale=0.3 * GUN_SCALE,
        position=(0, 0, 0.6),
        rotation_x=90,
        enabled=False
    )

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
# TRANSFORM UPDATES
# ------------------------------
def set_gun_transform(pos=None, rot=None, scale=None):
    global GUN_POS, GUN_ROT, GUN_SCALE
    if pos: 
        GUN_POS = Vec3(pos)
        if gun: gun.position = GUN_POS
    if rot: 
        GUN_ROT = Vec3(rot)
        if gun: gun.rotation = GUN_ROT
    if scale: 
        GUN_SCALE = scale
        if gun: gun.scale = GUN_SCALE

# ------------------------------
# RECOIL & MUZZLE
# ------------------------------
def do_recoil():
    global recoil_active
    if not gun or recoil_active:
        return
    
    recoil_active = True
    
    # Recoil: move gun back and slightly up (more pronounced)
    recoil_offset = Vec3(0, 0.05, -0.3 * GUN_SCALE)
    recoil_pos = GUN_POS + recoil_offset
    
    # Immediately move gun back
    gun.position = recoil_pos
    
    # Animate back to original position
    gun.animate_position(GUN_POS, duration=0.25, curve=curve.in_out_quad)
    
    # Reset recoil flag after animation
    def reset_recoil():
        global recoil_active
        recoil_active = False
    invoke(reset_recoil, delay=0.25)
    
    # Also add camera rotation recoil (if player has camera_pivot)
    if player and hasattr(player, 'camera_pivot'):
        original_rot_x = player.camera_pivot.rotation_x
        # Kick camera up more noticeably
        player.camera_pivot.rotation_x = original_rot_x + 3.0
        player.camera_pivot.animate('rotation_x', original_rot_x, duration=0.25, curve=curve.in_out_quad)

def do_muzzle_flash():
    if muzzle_flash:
        muzzle_flash.enabled = True
        muzzle_flash.animate_scale(0.6 * GUN_SCALE, duration=0.05)
        muzzle_flash.animate_scale(0.0, duration=0.05, delay=0.05)
        invoke(setattr, muzzle_flash, 'enabled', False, delay=0.1)

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
        gun.animate_position(GUN_POS + Vec3(0, -0.4 * GUN_SCALE, 0), duration=0.2)
        gun.animate_position(GUN_POS + Vec3(0, -0.4 * GUN_SCALE, 0), duration=reload_time-0.4, delay=0.2)
        gun.animate_position(GUN_POS, duration=0.2, delay=reload_time-0.2)
    
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
