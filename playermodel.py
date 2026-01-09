from ursina import *
import math

# Player model configuration
DEFAULT_Y_OFFSET = 1.2


def _exclude_from_raycast(entity, controller=None):
    """
    Exclude an entity from raycast traversal to prevent errors.
    
    Args:
        entity: The entity to exclude
        controller: Optional FirstPersonController to add entity to its ignore_list
    """
    # Add to controller's ignore_list if provided
    if controller is not None:
        if not hasattr(controller, 'ignore_list') or controller.ignore_list is None:
            controller.ignore_list = []
        if entity not in controller.ignore_list:
            controller.ignore_list.append(entity)
    
    # Disable collision detection on the nodePath
    try:
        if hasattr(entity, 'nodePath') and entity.nodePath:
            entity.nodePath.setCollideMask(0)
    except:
        pass


def attach_playermodel_to_controller(controller, model_path=None):
    """
    Attach a minimal placeholder entity to a FirstPersonController.
    Since the playermodel is invisible, we use a simple placeholder to avoid
    loading FBX files that contain problematic animation channels.
    
    Args:
        controller: The FirstPersonController to attach the model to
        model_path: Not used (kept for compatibility)
        
    Returns:
        True if placeholder was successfully attached, False otherwise
    """
    try:
        # Create a minimal invisible placeholder entity
        # We don't load the FBX because it contains animation channels that cause crashes
        controller.playermodel = Entity(
            parent=controller,
            model='cube',  # Simple cube model, no animations
            scale=0.01,    # Tiny, invisible
            y=-0.4,
            visible=False,  # Hidden for first-person view
        )
        
        # Exclude from raycast traversal
        _exclude_from_raycast(controller.playermodel, controller)
        
        # Don't set controller.animations - it conflicts with Ursina's internal animation system
        # Ursina uses animations as a list for animation sequences, not a dict
        # We don't need to track animations since we're not using them anyway
        controller._playermodel_animations_disabled = True
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not create playermodel placeholder: {e}")
        controller.playermodel = None
        controller._playermodel_animations_disabled = True
        return False


def update_player_animation(controller):
    """
    Update head/torso bob animation based on movement state.
    Simplified version that only handles head bob (no model animations).
    
    Args:
        controller: The FirstPersonController with attached playermodel
    """
    if not controller:
        return
        
    if not hasattr(controller, "playermodel") or controller.playermodel is None:
        return
    
    try:
        pm = controller.playermodel
        if not pm or not hasattr(pm, 'y'):
            return
        
        # Check if player is moving
        moving = any(held_keys.get(k, 0) for k in ("w", "a", "s", "d", "q", "e"))
        
        # Head/torso bob for first-person feel
        if moving:
            if not hasattr(controller, 'bob_phase'):
                controller.bob_phase = 0.0
            controller.bob_phase += time.dt * 9
            bob = math.sin(controller.bob_phase) * 0.05
            lean = math.sin(controller.bob_phase * 0.5) * 3
        else:
            if not hasattr(controller, 'bob_phase'):
                controller.bob_phase = 0.0
            controller.bob_phase = max(controller.bob_phase - time.dt * 6, 0)
            bob = 0
            lean = 0
        
        base_y = getattr(controller, 'base_y', DEFAULT_Y_OFFSET)
        pm.y = base_y + bob
        pm.rotation_z = lean
        pm.rotation_x = lean * 0.3
    except:
        # Silently fail if playermodel is destroyed or inaccessible
        pass


def spawn_static_playermodel(position=Vec3(3, 0, 6), scale=1.0, model_path=None):
    """
    Spawn a simple static placeholder in the world.
    Uses a simple cube instead of the FBX to avoid animation channel issues.
    
    Args:
        position: World position to spawn at
        scale: Scale of the model
        model_path: Not used (kept for compatibility)
        
    Returns:
        Entity representing the static playermodel
    """
    try:
        # Use a simple cube instead of the FBX file to avoid animation channels
        ent = Entity(
            model='cube',
            position=position,
            scale=scale,
            collider="box",
            color=color.gray,
        )
        
        # Exclude from raycast traversal
        _exclude_from_raycast(ent)
        
    except Exception as e:
        print(f"Error: Could not create static playermodel: {e}")
        # Create a minimal placeholder
        ent = Entity(
            model='cube',
            position=position,
            scale=scale,
            collider="box",
            color=color.gray,
        )
    
    return ent
