from ursina import *

# --- LOADING SCREEN GLOBALS ---
loading_panel = None
loading_text = None
loading_sub = None
loading_spinner = None
loading_dots = ""

def show_loading_screen(message="Loading..."):
    """Show a loading screen with a message."""
    global loading_panel, loading_text, loading_sub, loading_spinner, loading_dots
    
    # Dark background panel
    loading_panel = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 0.86),
        scale=(2, 2, 1),
        position=(0, 0, -0.1),
        z=-0.1,
    )
    
    # Foreground card
    card = Entity(
        parent=loading_panel,
        model='quad',
        scale=(0.95, 0.4, 1),
        color=color.rgba(0.12, 0.12, 0.12, 0.94),
        z=-0.05,
    )
    Entity(
        parent=card,
        model='quad',
        scale=(1.02, 1.08, 1),
        color=color.rgba(1, 1, 1, 0.14),
        z=0.01,
    )
    
    # Loading text (title)
    loading_text = Text(
        text=message,
        parent=card,
        position=(0, 0.08, -0.1),
        origin=(0.5, 0.5),
        scale=1.8,
        color=color.white,
        bold=True,
    )
    
    # Subtext
    loading_sub = Text(
        text="Please wait",
        parent=card,
        position=(0, -0.02, -0.1),
        origin=(0.5, 0.5),
        scale=1.1,
        color=color.rgba(200, 200, 200, 255),
    )

    # Simple spinner dot
    loading_spinner = Text(
        text="*",
        parent=card,
        position=(0.32, -0.12, -0.1),  # right side, acts as dot carrier
        origin=(0, 0.5),
        scale=1.2,
        color=color.azure,
    )
    
    loading_dots = ""

def update_loading_screen(message=None):
    """Update the loading screen message with animated dots."""
    global loading_text, loading_sub, loading_spinner, loading_dots
    
    if loading_text is None:
        return
    
    # Animate dots
    loading_dots = (loading_dots + ".") if len(loading_dots) < 3 else ""
    
    # Keep the base label static and append dots separately to avoid shifting center
    base_title = message if message is not None else loading_text.text.split(".")[0]
    loading_text.text = base_title
    # Place dots with a separate Text so centering is stable
    # (reuse spinner entity as dot carrier to avoid extra entity)
    if loading_spinner:
        loading_spinner.text = "." * len(loading_dots) if loading_dots else ""

    if loading_sub:
        loading_sub.text = "Still working"

    if loading_spinner:
        palette = [color.azure, color.cyan, color.lime, color.yellow, color.orange, color.violet]
        idx = len(loading_dots) % len(palette)
        loading_spinner.color = palette[idx]

def hide_loading_screen():
    """Hide and destroy the loading screen."""
    global loading_panel, loading_text, loading_sub, loading_spinner, loading_dots
    
    if loading_panel:
        destroy(loading_panel)
        loading_panel = None
    
    if loading_text:
        destroy(loading_text)
        loading_text = None
    
    if loading_sub:
        destroy(loading_sub)
        loading_sub = None

    if loading_spinner:
        destroy(loading_spinner)
        loading_spinner = None
    
    loading_dots = ""
