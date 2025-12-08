from ursina import *

# --- LOADING SCREEN GLOBALS ---
loading_panel = None
loading_text = None
loading_dots = ""

def show_loading_screen(message="Loading..."):
    """Show a loading screen with a message."""
    global loading_panel, loading_text, loading_dots
    
    # Dark background panel
    loading_panel = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 220),
        scale=(2, 2, 1),
        position=(0, 0, -0.1),
        z=-0.1
    )
    
    # Loading text
    loading_text = Text(
        text=message,
        parent=camera.ui,
        position=(0, 0.1, -0.2),
        origin=(0.5, 0.5),
        scale=2,
        color=color.white,
        bold=True
    )
    
    loading_dots = ""

def update_loading_screen(message=None):
    """Update the loading screen message with animated dots."""
    global loading_text, loading_dots
    
    if loading_text is None:
        return
    
    # Animate dots
    loading_dots = (loading_dots + ".") if len(loading_dots) < 3 else ""
    
    if message:
        loading_text.text = message + loading_dots
    else:
        loading_text.text = loading_text.text.split(".")[0] + loading_dots

def hide_loading_screen():
    """Hide and destroy the loading screen."""
    global loading_panel, loading_text, loading_dots
    
    if loading_panel:
        destroy(loading_panel)
        loading_panel = None
    
    if loading_text:
        destroy(loading_text)
        loading_text = None
    
    loading_dots = ""
