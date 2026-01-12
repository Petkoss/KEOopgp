from ursina import *
import math
from pathlib import Path

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
            # Set collide mask to 0 to exclude from all collision/raycast checks
            entity.nodePath.setCollideMask(0)
            # Also try to exclude from traversals
            entity.nodePath.setTag('raycast_ignore', '1')
            # Hide from camera culling to prevent traversal issues
            entity.nodePath.hide()
            entity.nodePath.show()  # Show the model but exclude from raycast
    except Exception as e:
        # Silently ignore if we can't modify the nodePath
        pass


def attach_playermodel_to_controller(controller, model_path=None):
    """
    Attach a player model (GLB) to a FirstPersonController.
    
    Args:
        controller: The FirstPersonController to attach the model to
        model_path: Optional path to model file (defaults to john_wick_fortnite.glb)
        
    Returns:
        True if model was successfully attached, False otherwise
    """
    try:
        # Use the specified model path or default to john_wick_fortnite.glb
        if model_path is None:
            model_path = 'assets/john_wick_fortnite.glb'
        
        # Load the GLB model
        controller.playermodel = Entity(
            parent=controller,
            model=model_path,
            scale=(0.75, 3, 0.75),  # 5x taller than default
            y=DEFAULT_Y_OFFSET,  # Position at default offset
            visible=False,  # Hidden for first-person view
        )
        
        # Exclude from raycast traversal - CRITICAL to prevent raycast errors
        _exclude_from_raycast(controller.playermodel, controller)
        
        # Check if model has animations
        has_animations = False
        try:
            if hasattr(controller.playermodel, 'model') and controller.playermodel.model:
                if hasattr(controller.playermodel.model, 'animations'):
                    anims = controller.playermodel.model.animations
                    if anims and (isinstance(anims, dict) or (isinstance(anims, list) and len(anims) > 0)):
                        has_animations = True
        except:
            pass
        
        controller._has_animations = has_animations
        controller._playermodel_animations_disabled = not has_animations  # Disable if no animations found
        
        print(f"✓ Player model '{model_path}' attached (animations: {has_animations})")
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not load playermodel '{model_path}': {e}")
        # Fallback to cube placeholder
        try:
            controller.playermodel = Entity(
                parent=controller,
                model='cube',
                scale=(0.3, 2.4, 0.3),
                y=1.2,
                visible=False,
            )
            _exclude_from_raycast(controller.playermodel, controller)
            print("✓ Fallback cube playermodel attached")
        except:
            pass
        controller.playermodel = None
        controller._playermodel_animations_disabled = True
        controller._has_animations = False
        return False


def update_player_animation(controller):
    """
    Update player animations based on movement state.
    Handles both FBX model animations and head/torso bob.
    Note: Model animations are disabled to prevent assertion errors, but head bob still works.
    
    Args:
        controller: The FirstPersonController with attached playermodel
    """
    if not controller:
        return
        
    if not hasattr(controller, "playermodel") or controller.playermodel is None:
        return
    
    # Check if animations are disabled (they are, to prevent assertion errors)
    animations_disabled = getattr(controller, '_playermodel_animations_disabled', False)
    
    try:
        pm = controller.playermodel
        if not pm or not hasattr(pm, 'y'):
            return
        
        # Check if player is moving
        moving = any(held_keys.get(k, 0) for k in ("w", "a", "s", "d", "q", "e"))
        sprinting = held_keys.get("left control", False) and moving
        
        # Skip FBX model animations if disabled (they cause assertion errors)
        # But still do head bob animation
        if not animations_disabled:
            # Determine animation state
            if sprinting:
                target_animation = "run"
            elif moving:
                target_animation = "walk"
            else:
                target_animation = "idle"
            
            # Update FBX model animations if available
            if getattr(controller, '_has_animations', False):
                try:
                    # Check if animation changed
                    current_anim = getattr(controller, '_current_animation', None)
                    if current_anim != target_animation:
                        controller._current_animation = target_animation
                        
                        # Try to play the animation
                        # Ursina animations can be accessed through the model or entity
                        try:
                            # Method 1: Try entity animations
                            if hasattr(pm, 'animations'):
                                anims = pm.animations
                                if isinstance(anims, dict) and target_animation in anims:
                                    pm.animations[target_animation].play()
                                elif isinstance(anims, list) and len(anims) > 0:
                                    # If it's a list, try common animation names
                                    for anim in anims:
                                        if target_animation.lower() in str(anim).lower():
                                            anim.play()
                                            break
                            
                            # Method 2: Try model animations
                            if hasattr(pm, 'model') and pm.model:
                                if hasattr(pm.model, 'animations'):
                                    anims = pm.model.animations
                                    if isinstance(anims, dict) and target_animation in anims:
                                        pm.model.animations[target_animation].play()
                                    elif isinstance(anims, list) and len(anims) > 0:
                                        for anim in anims:
                                            if target_animation.lower() in str(anim).lower():
                                                anim.play()
                                                break
                            
                            # Method 3: Try direct animation access via nodePath
                            if hasattr(pm, 'nodePath') and pm.nodePath:
                                # Try common animation names
                                anim_names = [target_animation, f"{target_animation}_loop", f"Armature|{target_animation}"]
                                for anim_name in anim_names:
                                    try:
                                        anim = pm.nodePath.find(f"**/{anim_name}")
                                        if anim and not anim.isEmpty():
                                            # Animation found, play it
                                            pass  # Ursina handles this automatically
                                            break
                                    except:
                                        pass
                        except Exception as anim_error:
                            # Silently continue if animation play fails
                            pass
                except Exception as e:
                    # Animation system error, continue with head bob
                    pass
        
        # Head/torso bob for first-person feel
        if moving:
            if not hasattr(controller, 'bob_phase'):
                controller.bob_phase = 0.0
            bob_speed = 12 if sprinting else 9
            controller.bob_phase += time.dt * bob_speed
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
    Spawn a static player model (GLB) in the world that can be damaged and destroyed.
    
    Args:
        position: World position to spawn at
        scale: Scale multiplier for the model
        model_path: Optional path to model file (defaults to john_wick_fortnite.glb)
        
    Returns:
        Entity representing the static playermodel
    """
    try:
        # Use the specified model path or default to john_wick_fortnite.glb
        if model_path is None:
            model_path = 'assets/john_wick_fortnite.glb'
        
        # Load the GLB model
        ent = Entity(
            model=model_path,
            position=position,
            scale=(scale, scale * 5, scale),  # 5x taller than default
            collider="box",  # Box collider for hit detection
            visible=True,  # Ensure it's visible
            enabled=True,  # Ensure it's enabled
        )
        
        # Ensure collider is properly set up for raycast detection
        if hasattr(ent, 'collider') and ent.collider:
            try:
                if hasattr(ent.collider, 'enabled'):
                    ent.collider.enabled = True
            except:
                pass
        
        # Mark as player target immediately (will be set again in player.py, but this ensures it's set)
        ent.is_player_target = True
        
        # DO NOT exclude from raycast - we want it to be hittable
        # The entity will be treated as a player target and can take damage
        
    except Exception as e:
        print(f"Error: Could not create static playermodel: {e}")
        # Fallback to cube placeholder
        try:
            cube_height = 2.4 * scale
            adjusted_position = Vec3(position.x, position.y + cube_height / 2, position.z)
            ent = Entity(
                model='cube',
                position=adjusted_position,
                scale=(0.3 * scale, cube_height, 0.3 * scale),
                collider="box",
                color=color.white,  # White cube for visibility
            )
            ent.is_player_target = True
        except:
            ent = None
    
    return ent
