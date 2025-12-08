from ursina import *

# ------------------------------
# GUN EFFECTS GLOBALS
# ------------------------------
gun_entity = None
muzzle_flash_entity = None
GUN_POS = Vec3(0.75, -0.8, 1)
GUN_ROT = Vec3(270, 90, 184)
GUN_SCALE = 1.0
recoil_active = False

# ------------------------------
# INITIALIZE GUN EFFECTS
# ------------------------------
def setup_gun_effects(gun, muzzle_flash, gun_pos, gun_rot, gun_scale):
    """Initialize gun effects with references to gun entities."""
    global gun_entity, muzzle_flash_entity, GUN_POS, GUN_ROT, GUN_SCALE
    gun_entity = gun
    muzzle_flash_entity = muzzle_flash
    GUN_POS = Vec3(gun_pos) if gun_pos else Vec3(0.75, -0.8, 1)
    GUN_ROT = Vec3(gun_rot) if gun_rot else Vec3(270, 90, 184)
    GUN_SCALE = gun_scale if gun_scale else 1.0

# ------------------------------
# RECOIL EFFECTS
# ------------------------------
def do_recoil(player=None):
    """
    Apply recoil animation to the gun.
    Moves gun back and up, then animates back to original position.
    Also applies camera kick if player is provided.
    Works with both cube placeholder and rifle model.
    """
    global recoil_active, GUN_POS, GUN_SCALE
    
    if not gun_entity or recoil_active:
        return
    
    recoil_active = True
    
    # Calculate recoil offset based on gun scale
    # For rifle models, recoil moves back (negative Z in camera space) and slightly up
    # Adjust based on gun scale to work with different model sizes
    recoil_back = -0.4 * GUN_SCALE  # Move back
    recoil_up = 0.1 * GUN_SCALE     # Move up slightly
    
    recoil_offset = Vec3(0, recoil_up, recoil_back)
    recoil_pos = GUN_POS + recoil_offset
    
    # Immediately move gun back for instant feedback
    gun_entity.position = recoil_pos
    
    # Animate back to original position smoothly
    gun_entity.animate_position(GUN_POS, duration=0.2, curve=curve.out_quad)
    
    # Reset recoil flag after animation completes
    def reset_recoil():
        global recoil_active
        recoil_active = False
    invoke(reset_recoil, delay=0.2)
    
    # Apply camera rotation recoil (kick up)
    if player and hasattr(player, 'camera_pivot'):
        original_rot_x = player.camera_pivot.rotation_x
        # Kick camera up - amount scales with gun scale
        kick_amount = 2.5 * min(GUN_SCALE, 1.5)  # Cap at 1.5x scale
        player.camera_pivot.rotation_x = original_rot_x + kick_amount
        player.camera_pivot.animate('rotation_x', original_rot_x, duration=0.2, curve=curve.out_quad)
    elif player and hasattr(player, 'rotation_x'):
        # Fallback if no camera_pivot
        original_rot_x = player.rotation_x
        kick_amount = 2.0 * min(GUN_SCALE, 1.5)
        player.rotation_x = original_rot_x + kick_amount
        player.animate('rotation_x', original_rot_x, duration=0.2, curve=curve.out_quad)

# ------------------------------
# MUZZLE FLASH EFFECTS
# ------------------------------
def do_muzzle_flash():
    """
    Create a muzzle flash effect at the gun's muzzle.
    Flashes bright yellow/orange and quickly fades out.
    Works with both cube placeholder and rifle model.
    """
    global muzzle_flash_entity, GUN_SCALE
    
    if not muzzle_flash_entity:
        return
    
    # Enable muzzle flash
    muzzle_flash_entity.enabled = True
    
    # Calculate scale based on gun scale
    # For rifle models, use slightly larger flash
    initial_scale = 0.4 * GUN_SCALE
    
    # Set initial scale and make it visible
    muzzle_flash_entity.scale = initial_scale
    muzzle_flash_entity.color = color.yellow
    
    # Flash animation: quick pop and fade
    # First, scale up slightly for the flash
    muzzle_flash_entity.animate_scale(initial_scale * 1.5, duration=0.03)
    
    # Then quickly fade out by scaling down and changing color
    muzzle_flash_entity.animate_scale(0.0, duration=0.07, delay=0.03)
    muzzle_flash_entity.animate_color(color.orange, duration=0.05, delay=0.03)
    muzzle_flash_entity.animate_color(color.rgba(255, 100, 0, 0), duration=0.05, delay=0.08)
    
    # Disable after animation completes
    invoke(setattr, muzzle_flash_entity, 'enabled', False, delay=0.1)
    # Reset color for next flash
    invoke(setattr, muzzle_flash_entity, 'color', color.yellow, delay=0.1)

# ------------------------------
# UPDATE GUN POSITION (for dynamic updates)
# ------------------------------
def update_gun_position(new_pos):
    """Update the base gun position (called when gun transform changes)."""
    global GUN_POS
    GUN_POS = Vec3(new_pos)

def update_gun_scale(new_scale):
    """Update the gun scale (affects recoil and muzzle flash intensity)."""
    global GUN_SCALE
    GUN_SCALE = new_scale

def update_gun_rotation(new_rot):
    """Update the gun rotation."""
    global GUN_ROT
    GUN_ROT = Vec3(new_rot)

# ------------------------------
# GUN TRANSFORM UPDATES
# ------------------------------
def set_gun_transform(pos=None, rot=None, scale=None):
    """
    Update gun position, rotation, and/or scale.
    Updates both the gun entity and internal state.
    """
    global GUN_POS, GUN_ROT, GUN_SCALE, gun_entity
    
    if pos: 
        GUN_POS = Vec3(pos)
        if gun_entity: 
            gun_entity.position = GUN_POS
        update_gun_position(GUN_POS)
    
    if rot: 
        GUN_ROT = Vec3(rot)
        if gun_entity: 
            gun_entity.rotation = GUN_ROT
        update_gun_rotation(GUN_ROT)
    
    if scale: 
        GUN_SCALE = scale
        if gun_entity: 
            gun_entity.scale = GUN_SCALE
        update_gun_scale(GUN_SCALE)
