from ursina import *

crosshair = None

def setup_crosshair():
    """Create a + crosshair in the center of the screen"""
    global crosshair
    
    # Remove existing crosshair if any
    if crosshair:
        destroy(crosshair)
    
    # Create crosshair container (invisible, no model)
    crosshair = Entity(parent=camera.ui)
    crosshair.model = None
    crosshair.visible = False
    
    # Horizontal line (left part)
    Entity(
        parent=crosshair,
        model='quad',
        color=color.white,
        scale=(0.02, 0.002),
        position=(-0.015, 0, 0)
    )
    
    # Horizontal line (right part)
    Entity(
        parent=crosshair,
        model='quad',
        color=color.white,
        scale=(0.02, 0.002),
        position=(0.015, 0, 0)
    )
    
    # Vertical line (top part)
    Entity(
        parent=crosshair,
        model='quad',
        color=color.white,
        scale=(0.002, 0.02),
        position=(0, 0.015, 0)
    )
    
    # Vertical line (bottom part)
    Entity(
        parent=crosshair,
        model='quad',
        color=color.white,
        scale=(0.002, 0.02),
        position=(0, -0.015, 0)
    )

