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


def create_player(position=Vec3(0, 3, -2), speed=5, jump_height=2):
    """
    Create and configure the local player controller with soldier character model.
    """
    controller = FirstPersonController(
        speed=speed,
        jump_height=jump_height,
        position=position,
        collider="box",
    )
    controller.scale_y = DEFAULT_HEIGHT
    if controller.collider is None:
        controller.collider = "box"

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


def setup_local_player(position=Vec3(0, 2, -2), normal_speed=5, sprint_speed=10, jump_height=2):
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


def spawn_static_playermodel(position=Vec3(3, 0, 6), scale=1.0):
    """
    Spawn a non-moving soldier character model in the world (for showcase/testing).
    """
    ent = playermodel.spawn_static_playermodel(position=position, scale=scale)
    _attach_health(ent)
    return ent

