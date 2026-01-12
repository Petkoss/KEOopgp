from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import playermodel

DEFAULT_HEIGHT = 2.4
DEFAULT_Y_OFFSET = 1.2
DEFAULT_HEALTH = 100


def _attach_health(entity, max_health=DEFAULT_HEALTH, on_death=None):
    """
    Make an entity damageable by giving it health-related attributes.
    """
    entity.max_health = max_health
    entity.health = max_health
    entity.is_player_target = True  # flag so gun logic can distinguish players
    entity._on_player_death = on_death


def apply_player_damage(target, amount):
    """
    Apply damage to any entity that was marked as a player target.
    Returns True if damage was applied.
    """
    if not getattr(target, "is_player_target", False):
        return False

    # Ensure the target has basic health fields
    if not hasattr(target, "health"):
        _attach_health(target)

    if getattr(target, "health", 0) <= 0:
        return True  # already dead

    target.health = max(0, target.health - amount)
    if target.health <= 0:
        death_cb = getattr(target, "_on_player_death", None)
        if callable(death_cb):
            death_cb()
        else:
            destroy(target)
    return True


def create_player(position=Vec3(0, 3, -2), speed=1, jump_height=1.5):
    """
    Create and configure the local player controller with tall cube model.
    """
    controller = FirstPersonController(
        speed=speed,
        jump_height=jump_height,
        position=position,
        collider="box",
    )
    # Set scale to match cube dimensions: width/depth 0.3, height 2.4
    controller.scale_x = 0.3
    controller.scale_y = DEFAULT_HEIGHT  # 2.4
    controller.scale_z = 0.3
    
    # Ensure collider is properly set up and enabled for physics
    if controller.collider is None:
        controller.collider = "box"
    
    # Make sure collider is enabled for physics collisions
    try:
        if hasattr(controller.collider, 'enabled'):
            controller.collider.enabled = True
        # The collider will automatically match the entity's scale (0.3 x 2.4 x 0.3)
        # This ensures the hitbox matches the entire cube
    except Exception as e:
        print(f"Warning: Could not fully configure player collider: {e}")
    
    # Ensure the controller can move properly - disable collision with certain entities if needed
    try:
        # Make sure gravity and movement are enabled
        if hasattr(controller, 'gravity'):
            controller.gravity = 1
        if hasattr(controller, 'jump_height'):
            controller.jump_height = jump_height
    except Exception as e:
        print(f"Warning: Could not configure controller movement: {e}")
    
    print(f"✓ Player created at {position}, collider={type(controller.collider).__name__ if controller.collider else 'None'}, scale=({controller.scale_x}, {controller.scale_y}, {controller.scale_z})")

    # Give the controller baseline health so it can receive player-vs-player damage
    _attach_health(controller)

    # Attach player model with animations (handled by playermodel module)
    playermodel.attach_playermodel_to_controller(controller)

    controller.bob_phase = 0.0
    controller.base_y = DEFAULT_Y_OFFSET
    controller.base_rot_z = 0
    controller.base_rot_x = 0
    controller.is_jumping = False
    controller.is_grounded = True
    return controller


def setup_local_player(position=Vec3(0, 2, -2), normal_speed=1, sprint_speed=4, jump_height=1.5):
    """
    Factory that creates the player and handles mouse locking defaults.
    """
    controller = create_player(position=position, speed=normal_speed, jump_height=jump_height)
    controller.normal_speed = normal_speed
    controller.sprint_speed = sprint_speed
    mouse.locked = True
    mouse.visible = False
    return controller


def update_local_player(controller):
    """
    Apply per-frame player updates: speed toggle and animation.
    """
    if not controller:
        return
    controller.speed = controller.sprint_speed if held_keys.get("left control", False) else controller.normal_speed
    
    # Update grounded state (check if player is on ground)
    # FirstPersonController has gravity, so check y velocity
    try:
        if hasattr(controller, "velocity"):
            controller.is_grounded = abs(controller.velocity.y) < 0.1
        elif hasattr(controller, "y"):
            # Fallback: check if y position is stable (not falling)
            if not hasattr(controller, "_last_y"):
                controller._last_y = controller.y
            if abs(controller.y - controller._last_y) < 0.01:
                controller.is_grounded = True
            else:
                controller.is_grounded = False
            controller._last_y = controller.y
        else:
            controller.is_grounded = True
    except:
        controller.is_grounded = True
    
    playermodel.update_player_animation(controller)


def spawn_static_playermodel(position=Vec3(3, 0, 6), scale=1.0, max_health=100):
    """
    Spawn a non-moving tall cube model in the world that can be damaged and destroyed.
    
    Args:
        position: World position to spawn at
        scale: Scale multiplier for the model
        max_health: Maximum health points (default: 100)
    """
    ent = playermodel.spawn_static_playermodel(position=position, scale=scale)
    
    # Define death callback to make entity disappear when health reaches 0
    def on_death():
        """Destroy the entity when it dies."""
        if ent and hasattr(ent, 'enabled'):
            print(f"💀 Static playermodel destroyed! Health reached 0.")
            destroy(ent)
    
    # Attach health with death callback and custom max_health
    _attach_health(ent, max_health=max_health, on_death=on_death)
    
    # Ensure the entity is marked as a player target
    ent.is_player_target = True
    
    return ent

