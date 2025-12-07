from ursina import *
import socket, json

menu_panel = None
name_input = None
ip_input = None
color_buttons = {}
play_button = None
error_text = None
selected_color = "red"

COLOR_OPTIONS = ["red","orange","yellow","green","cyan","blue","violet","pink"]
COLOR_MAP = {
    "red": color.red, "orange": color.orange, "yellow": color.yellow,
    "green": color.green, "cyan": color.cyan, "blue": color.blue,
    "violet": color.violet, "pink": color.pink
}

start_game_callback = None
def set_start_game_callback(cb): 
    global start_game_callback; start_game_callback = cb

def select_color(col):
    global selected_color
    if selected_color in color_buttons:
        b = color_buttons[selected_color]; b.color = COLOR_MAP[selected_color]; b.scale = b.original_scale
    selected_color = col
    if col in color_buttons:
        b = color_buttons[col]; b.scale = tuple(s * 1.25 for s in b.original_scale)

def connect_to_server():
    global error_text
    username = name_input.text.strip() or "Player"
    server_ip = ip_input.text.strip()
    if not server_ip:
        error_text.text, error_text.color = "Please enter a server IP!", color.red; return
    error_text.text, error_text.color = "Connecting...", color.azure
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((server_ip, 9999))
        data = sock.recv(4096).decode()
        my_id = json.loads(data)["id"]
        sock.sendall(json.dumps({"name": username, "color": selected_color}).encode())
        if menu_panel: menu_panel.enabled = False
        error_text.text = ""
        if start_game_callback: start_game_callback(sock, my_id, username, selected_color)
    except socket.timeout:
        error_text.text, error_text.color = "Connection timeout! Check IP address.", color.red
    except Exception as e:
        error_text.text, error_text.color = f"Connection failed: {e}", color.red
    finally:
        try:
            if sock: sock.settimeout(None)
        except: pass

def _set_input_text_props(inp, scale_val, col):
    try:
        if hasattr(inp, 'text_entity') and inp.text_entity:
            inp.text_entity.color, inp.text_entity.scale = col, scale_val
        elif hasattr(inp, 'text_field'):
            tf = inp.text_field
            if hasattr(tf, 'text_entity') and tf.text_entity:
                tf.text_entity.color, tf.text_entity.scale = col, scale_val
    except: pass

def _add_border(entity, border_width=0.003, border_color=color.white):
    """Add a border around an entity"""
    border_scale = (entity.scale_x + border_width, entity.scale_y + border_width)
    border = Entity(parent=entity.parent, model='quad', 
                   color=border_color, scale=border_scale, 
                   position=(entity.x, entity.y, entity.z + 0.001))
    return border

def create_menu():
    global menu_panel, name_input, ip_input, color_buttons, play_button, error_text
    color_buttons = {}
    BASE_H = 1080
    try:
        screen_h = window.size.y
    except:
        screen_h = BASE_H
    ui_scale = max(0.6, min(screen_h / BASE_H, 3.0))
    TEXT_MULTIPLIER = 20

    panel_scale = (0.85, 0.85)
    if menu_panel:
        destroy(menu_panel, delay=0)
    menu_panel = Entity(parent=camera.ui, model='quad',
                        color=color.rgba(25,25,25,230), scale=panel_scale, position=(0,0), z=0.5)

    ph, pw = panel_scale[1], panel_scale[0]
    # Use fixed spacing for better control
    top = ph * 0.45
    bottom = -ph * 0.45
    
    # Title
    title = Text("GTA MINI", parent=menu_panel, x=0, y=top,
                 scale=0.24 * ui_scale * TEXT_MULTIPLIER, color=color.azure, weight='bold', origin=(0,0))

    # Player Name section
    name_y = top - 0.12
    name_label = Text("Player Name", parent=menu_panel, x=0, y=name_y,
                      scale=0.08 * ui_scale * TEXT_MULTIPLIER, color=color.light_gray, origin=(0,0))
    input_w = pw * 0.65
    input_h = ph * 0.08
    name_input = InputField(parent=menu_panel, x=0, y=name_y - 0.06, scale=(input_w, input_h),
                            text="Player", max_length=20, color=color.white)
    name_input.hover_color = color.white  # Keep white on hover
    _set_input_text_props(name_input, 0.06 * ui_scale * TEXT_MULTIPLIER, color.black)
    _add_border(name_input, border_width=0.004, border_color=color.rgb(150,150,150))

    # Server IP section
    ip_y = name_y - 0.15
    ip_label = Text("Server IP", parent=menu_panel, x=0, y=ip_y,
                    scale=0.08 * ui_scale * TEXT_MULTIPLIER, color=color.light_gray, origin=(0,0))
    ip_input = InputField(parent=menu_panel, x=0, y=ip_y - 0.06, scale=(input_w, input_h),
                          text="127.0.0.1", max_length=45, color=color.white)
    ip_input.hover_color = color.white  # Keep white on hover
    _set_input_text_props(ip_input, 0.06 * ui_scale * TEXT_MULTIPLIER, color.black)
    _add_border(ip_input, border_width=0.004, border_color=color.rgb(150,150,150))

    # Color selection section
    color_y = ip_y - 0.15
    color_label = Text("Character Color", parent=menu_panel, x=0, y=color_y,
                       scale=0.08 * ui_scale * TEXT_MULTIPLIER, color=color.light_gray, origin=(0,0))

    cols = 4
    rows = (len(COLOR_OPTIONS) + cols - 1) // cols
    avail_w = pw * 0.75
    gap_x = avail_w * 0.05
    btn_w = (avail_w - (cols - 1) * gap_x) / cols
    btn_w = min(btn_w, ph * 0.10)
    total_row_width = cols * btn_w + (cols - 1) * gap_x
    start_x = - total_row_width / 2 + btn_w / 2
    y_colors = color_y - 0.08
    color_row_height = ph * 0.12
    for i, col in enumerate(COLOR_OPTIONS):
        cx = start_x + (i % cols) * (btn_w + gap_x)
        cy = y_colors - (i // cols) * color_row_height
        b = Button(parent=menu_panel, text="", scale=(btn_w, btn_w),
                   color=COLOR_MAP[col], position=(cx, cy))
        b.original_scale = (btn_w, btn_w)
        b.on_click = lambda c=col: select_color(c)
        color_buttons[col] = b

    if selected_color in color_buttons:
        color_buttons[selected_color].scale = tuple(s * 1.25 for s in color_buttons[selected_color].original_scale)

    # Play button - positioned to be clearly visible, moved lower from color selection
    play_y = y_colors - rows * color_row_height - 0.30
    # Ensure play button is above the bottom of the panel (but allow it to go lower)
    play_y = max(play_y, bottom)
    play_button = Button(text="PLAY", parent=menu_panel, x=0, y=play_y,
                         scale=(pw * 0.45, ph * 0.12), color=color.green)
    try:
        if hasattr(play_button, 'text_entity') and play_button.text_entity:
            play_button.text_entity.scale = 0.6 * ui_scale * TEXT_MULTIPLIER
            play_button.text_entity.color = color.black
    except: pass
    play_button.on_click = connect_to_server
    _add_border(play_button, border_width=0.005, border_color=color.rgb(200,200,200))

    # Error text at the bottom
    error_text = Text("", parent=menu_panel, x=0, y=bottom + 0.10,
                      scale=0.06 * ui_scale * TEXT_MULTIPLIER, color=color.red, origin=(0,0))

if __name__ == "__main__":
    app = Ursina()

    # Load the background texture explicitly (helps avoid path ambiguity).
    # Place the background in the 3D scene (parent=None/scene) and push it far away on the z axis
    # so it renders behind scene objects. UI (camera.ui) is always drawn on top of scene entities,
    # so the menu will remain above this background.
    try:
        tex = load_texture('assets/kosicebg.jpg')
    except Exception as e:
        print(f"Could not load background texture: {e}")
        tex = None

    if tex:
        # Compute a large scale so the quad fills the camera frustum
        # camera default is at z = -30 looking towards +z, so put background at positive z (farther away)
        z_pos = 80
        # Use aspect ratio to make the quad wide enough
        aspect = window.size.x / window.size.y if window.size.y else 16/9
        bg_scale_x = max(20 * aspect, 30)
        bg_scale_y = 30
        background = Entity(model='quad', texture=tex, double_sided=True,
                            scale=(bg_scale_x, bg_scale_y),
                            position=(0, 0, z_pos))
        # ensure it doesn't accidentally get parented to camera.ui later
        background.parent = scene

    create_menu()
    window.color = color.rgb(10,10,10)
    app.run()