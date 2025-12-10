from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math


DEFAULT_HEIGHT = 2.4
DEFAULT_Y_OFFSET = 1.2


def create_player(position=Vec3(0, 2, 0), speed=5, jump_height=2):
    """
    Create and configure the local player controller with a simple visible model.
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

    # Attach Steve model but keep it hidden for the local player (first-person)
    steve_model = "assets/Steve.glb"
    steve_tex = load_texture("assets/diffuse")
    controller.playermodel = Entity(
        parent=controller,
        model=steve_model,
        scale=1.0,
        y=-0.4,
        double_sided=True,
        visible=False,
    )

    controller.bob_phase = 0.0
    controller.base_y = DEFAULT_Y_OFFSET
    controller.base_rot_z = 0
    controller.base_rot_x = 0
    return controller


def setup_local_player(position=Vec3(0, 2, 0), normal_speed=5, sprint_speed=10, jump_height=2):
    """
    Factory that creates the player and handles mouse locking defaults.
    """
    controller = create_player(position=position, speed=normal_speed, jump_height=jump_height)
    controller.normal_speed = normal_speed
    controller.sprint_speed = sprint_speed
    mouse.locked = True
    mouse.visible = False
    return controller


def _is_moving():
    return any(
        held_keys.get(k, 0)
        for k in ("w", "a", "s", "d", "q", "e")
    )


def update_player_animation(controller):
    """
    Simple walk bob/lean for the attached playermodel.
    Call this from the main update loop.
    """
    if not controller or not hasattr(controller, "playermodel"):
        return

    moving = _is_moving()
    pm = controller.playermodel

    # Head/torso bob
    if moving:
        controller.bob_phase += time.dt * 9
        bob = math.sin(controller.bob_phase) * 0.05
        lean = math.sin(controller.bob_phase * 0.5) * 3
    else:
        controller.bob_phase = max(controller.bob_phase - time.dt * 6, 0)
        bob = 0
        lean = 0

    pm.y = controller.base_y + bob
    pm.rotation_z = lean
    pm.rotation_x = lean * 0.3


def update_local_player(controller):
    """
    Apply per-frame player updates: speed toggle and animation.
    """
    if not controller:
        return
    controller.speed = controller.sprint_speed if held_keys["left control"] else controller.normal_speed
    update_player_animation(controller)


def spawn_static_playermodel(position=Vec3(3, 0, 6), scale=1.0):
    """
    Spawn a non-moving Steve model in the world (for showcase/testing).
    """
    steve_model = "assets/Steve.glb"
    steve_tex = load_texture("diffuse")
    return Entity(
        model=steve_model,
        position=position,
        scale=scale,
        collider="box",
        double_sided=True,
    )

