from ursina import *
import socket, json

# Menu state
menu_panel = None
name_input = None
ip_input = None
color_buttons = {}
play_button = None
error_text = None
selected_color = "red"

# Color options
COLOR_OPTIONS = ["red", "orange", "yellow", "green", "cyan", "blue", "violet", "pink"]
COLOR_MAP = {
    "red": color.red, "orange": color.orange, "yellow": color.yellow,
    "green": color.green, "cyan": color.cyan, "blue": color.blue,
    "violet": color.violet, "pink": color.pink
}

# Callback function to start the game (set by client.py)
start_game_callback = None

def set_start_game_callback(callback):
    """Set the function to call when PLAY is clicked"""
    global start_game_callback
    start_game_callback = callback

def select_color(col):
    global selected_color
    # Reset previous selection
    if selected_color in color_buttons:
        color_buttons[selected_color].color = COLOR_MAP[selected_color]
        color_buttons[selected_color].scale = color_buttons[selected_color].original_scale

    # Set new selection
    selected_color = col
    if col in color_buttons:
        color_buttons[col].color = color.white
        color_buttons[col].scale = tuple(s * 1.2 for s in color_buttons[col].original_scale)

def connect_to_server():
    global error_text

    # Get inputs
    username = name_input.text.strip() if name_input.text.strip() else "Player"
    server_ip = ip_input.text.strip()

    if not server_ip:
        error_text.text = "Please enter a server IP!"
        return

    # Try to connect
    error_text.text = "Connecting..."
    error_text.color = color.black

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        sock.connect((server_ip, 9999))

        # Get player ID
        data = sock.recv(4096).decode()
        my_id = json.loads(data)["id"]

        # Send name and color
        sock.sendall(json.dumps({"name": username, "color": selected_color}).encode())

        # Hide menu
        if menu_panel:
            menu_panel.enabled = False
        error_text.text = ""

        # Start the game with connection info
        if start_game_callback:
            start_game_callback(sock, my_id, username, selected_color)

    except socket.timeout:
        error_text.text = "Connection timeout! Check IP address."
        error_text.color = color.black
        if sock:
            try:
                sock.close()
            except:
                pass
    except Exception as e:
        error_text.text = f"Connection failed: {str(e)}"
        error_text.color = color.black
        if sock:
            try:
                sock.close()
            except:
                pass

def create_menu():
    """
    Creates a responsive, nicely spaced menu for different screen sizes.
    The layout uses the panel's size to compute vertical spacing so it scales
    correctly across resolutions and aspect ratios.
    """
    global menu_panel, name_input, ip_input, color_buttons, play_button, error_text

    # Reset possible previous state
    color_buttons = {}

    # ============================================
    # DYNAMIC SCALING SYSTEM
    # ============================================
    # Base resolution: 1920x1080 (16:9)
    BASE_WIDTH = 1920
    BASE_HEIGHT = 1080

    # Get current screen dimensions
    try:
        screen_width = window.size.x if hasattr(window, 'size') else BASE_WIDTH
        screen_height = window.size.y if hasattr(window, 'size') else BASE_HEIGHT
    except:
        screen_width = BASE_WIDTH
        screen_height = BASE_HEIGHT

    # Calculate scale factors
    height_scale = screen_height / BASE_HEIGHT
    width_scale = screen_width / BASE_WIDTH
    aspect_ratio = screen_width / screen_height
    base_aspect = BASE_WIDTH / BASE_HEIGHT  # 16:9

    # UI scale (use height primarily)
    if aspect_ratio > base_aspect * 1.5:
        ui_scale = height_scale * 0.95
    elif aspect_ratio < base_aspect * 0.7:
        ui_scale = height_scale * 1.05
    else:
        ui_scale = height_scale
    ui_scale = max(0.5, min(ui_scale, 2.5))

    # Panel scale - occupy a sensible portion of the screen
    panel_w = min(1.6 * (aspect_ratio / base_aspect), 1.1)  # clamp width
    panel_h = 0.9  # relative height in UI units
    panel_scale = (panel_w, panel_h)

    # Try to load background image, fallback to solid color
    bg_texture = None
    try:
        import os
        image_files = ['background.jpg', 'background.png', 'background.jpeg',
                       'menu_bg.jpg', 'menu_bg.png', 'city.jpg', 'city.png',
                       'menu_background.jpg', 'menu_background.png']
        for img_file in image_files:
            if os.path.exists(img_file):
                bg_texture = load_texture(img_file)
                break
    except Exception:
        bg_texture = None

    # Clear any previous menu entities if present
    if menu_panel:
        destroy(menu_panel, delay=0)

    # Menu background
    if bg_texture:
        menu_bg = Entity(parent=camera.ui, model='quad', texture=bg_texture,
                         scale=(camera.aspect_ratio * 2, 2), position=(0, 0), z=1)
        # Dark overlay to improve contrast
        dark_overlay = Entity(parent=camera.ui, model='quad',
                              color=color.rgba(0, 0, 0, 150),
                              scale=(camera.aspect_ratio * 2, 2), position=(0, 0), z=0.9)
        menu_panel = Entity(parent=camera.ui, model='quad',
                            color=color.rgba(255, 255, 255, 230),
                            scale=panel_scale, position=(0, 0), z=0.8)
    else:
        # Solid panel
        menu_panel = Entity(parent=camera.ui, model='quad',
                            color=color.rgba(250, 250, 250, 240),
                            scale=panel_scale, position=(0, 0), z=0.5)

    # Compute layout positions relative to panel height so scaling is consistent
    ph = panel_scale[1]  # panel height (in UI units)
    pw = panel_scale[0]  # panel width

    # Vertical layout slots (fractions of panel height)
    y_top = ph * 0.38
    y_after_title = ph * 0.16
    y_name_input = ph * 0.06
    y_between = ph * 0.14
    y_ip_input = -ph * 0.06
    y_color_label = -ph * 0.18
    y_colors = -ph * 0.30
    y_play = -ph * 0.46
    y_error = -ph * 0.58

    # Font / label scales using ui_scale
    title_scale = 0.16 * ui_scale
    label_scale = 0.06 * ui_scale
    input_text_scale = 0.045 * ui_scale
    button_text_scale = 0.07 * ui_scale
    error_scale = 0.05 * ui_scale

    # Title
    title = Text("GTA MINI", parent=menu_panel, y=y_top, scale=title_scale,
                 origin=(0, 0), color=color.black, x=0, weight='bold')

    # Name label and input
    name_label = Text("Player Name", parent=menu_panel, y=y_after_title,
                      scale=label_scale, origin=(0, 0), color=color.black, x=0)
    input_w = pw * 0.55
    input_h = ph * 0.09
    name_input = InputField(parent=menu_panel, y=y_name_input, scale=(input_w, input_h),
                            text="Player", max_length=20, x=0, origin=(0, 0))
    # set input text color & size if available
    try:
        if hasattr(name_input, 'text_field'):
            tf = getattr(name_input, 'text_field')
            if hasattr(tf, 'text_entity'):
                te = tf.text_entity
                te.color = color.black
                te.scale = input_text_scale
    except Exception:
        pass

    # IP label and input
    ip_label = Text("Server IP", parent=menu_panel, y=y_ip_input + ph * 0.06,
                    scale=label_scale, origin=(0, 0), color=color.black, x=0)
    ip_input = InputField(parent=menu_panel, y=y_ip_input - ph * 0.04, scale=(input_w, input_h),
                          text="127.0.0.1", max_length=45, x=0, origin=(0, 0))
    try:
        if hasattr(ip_input, 'text_field'):
            tf = getattr(ip_input, 'text_field')
            if hasattr(tf, 'text_entity'):
                te = tf.text_entity
                te.color = color.black
                te.scale = input_text_scale
    except Exception:
        pass

    # Color label
    color_label = Text("Character Color", parent=menu_panel, y=y_color_label,
                       scale=label_scale, origin=(0, 0), color=color.black, x=0)

    # Color buttons layout: 4 columns x 2 rows (adjust dynamically)
    cols = 4
    rows = (len(COLOR_OPTIONS) + cols - 1) // cols
    # compute available width inside panel for buttons
    avail_w = pw * 0.8
    # spacing and button size in panel units
    gap_x = avail_w * 0.06
    btn_w = (avail_w - (cols - 1) * gap_x) / cols
    btn_w = min(btn_w, ph * 0.12)  # don't let them be excessively tall
    # starting x to center the grid
    total_row_width = cols * btn_w + (cols - 1) * gap_x
    start_x = - total_row_width / 2 + btn_w / 2

    for i, col in enumerate(COLOR_OPTIONS):
        cx = start_x + (i % cols) * (btn_w + gap_x)
        cy = y_colors - (i // cols) * (ph * 0.14)
        btn = Button(parent=menu_panel, text="", scale=(btn_w, btn_w),
                     color=COLOR_MAP[col], position=(cx, cy), origin=(0, 0))
        # remember original scale so selection can scale relative to it
        btn.original_scale = (btn_w, btn_w)
        btn.color_name = col
        btn.on_click = lambda c=col: select_color(c)
        color_buttons[col] = btn

    # Highlight selected color
    if selected_color in color_buttons:
        cb = color_buttons[selected_color]
        cb.color = color.white
        cb.scale = tuple(s * 1.2 for s in cb.original_scale)

    # Play button
    play_w = pw * 0.4
    play_h = ph * 0.12
    play_button = Button(text="PLAY", parent=menu_panel, y=y_play,
                         scale=(play_w, play_h), color=color.rgb(92, 184, 92),
                         x=0, origin=(0, 0))
    # button text tweaks
    try:
        if hasattr(play_button, 'text_entity'):
            play_button.text_entity.color = color.black
            play_button.text_entity.scale = button_text_scale
    except Exception:
        pass
    play_button.on_click = connect_to_server

    # Error text
    error_text = Text("", parent=menu_panel, y=y_error, scale=error_scale,
                      origin=(0, 0), color=color.black, x=0)

if __name__ == "__main__":
    # quick test harness to run the menu
    app = Ursina()
    create_menu()
    window.color = color.rgb(20, 20, 20)
    app.run()