from ursina import *

# --- PAUSE MENU GLOBALS ---
paused = False
pause_panel = pause_label = pause_hint = continue_button = exit_button = None

# --- PAUSE MENU SETUP ---
def setup_pause_menu():
    global pause_panel, pause_label, pause_hint, continue_button, exit_button
    pause_panel = Entity(parent=camera.ui, model='quad', color=color.rgba(0,0,0,180),
                         scale=(0.7,0.4), enabled=False, position=(0, 0))
    pause_label = Text("Game Paused", parent=pause_panel, y=0.15, scale=2, origin=(0,0))
    pause_hint = Text("Press ESC to resume", parent=pause_panel, y=0.05, scale=1,
                      origin=(0,0), color=color.azure)
    continue_button = Button(text="Continue", parent=pause_panel, y=-0.05, scale=(0.4,0.12),
                            origin=(0, 0))
    continue_button.on_click = hide_pause_menu
    exit_button = Button(text="Exit Game", parent=pause_panel, y=-0.22, scale=(0.4,0.12),
                         color=color.red, origin=(0, 0))
    exit_button.on_click = application.quit

# --- PAUSE MENU FUNCTIONS ---
def hide_pause_menu():
    global paused
    paused = False
    if pause_panel: pause_panel.enabled = False
    mouse.locked = True
    mouse.visible = False

def show_pause_menu():
    global paused
    paused = True
    if pause_panel: pause_panel.enabled = True
    mouse.locked = False
    mouse.visible = True

def handle_pause_input(key, game_started):
    if not game_started: return
    if key=='escape':
        hide_pause_menu() if paused else show_pause_menu()

