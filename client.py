import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading, time, random
import menu
import city_generation
import pause_menu

# --- GLOBALS ---
sock = None
USERNAME = ""
my_id = None
game_started = False

server_players = {}          # player_id -> player_data

COLOR_MAP = {
    "red": color.red, "orange": color.orange, "yellow": color.yellow,
    "green": color.green, "cyan": color.cyan, "blue": color.azure,
    "violet": color.violet, "pink": color.pink
}

player = None
other_players = {}

# --- NETWORK LISTENER ---
def listen_thread():
    global server_players
    while True:
        try:
            data = sock.recv(8192)
            if not data: break
            msg = json.loads(data.decode())
            if msg.get("type") == "players":
                server_players = msg.get("players", {})
        except:
            time.sleep(0.05)


# --- GAME SETUP ---
def start_game(connection_sock, player_id, username, selected_color):
    global sock, my_id, USERNAME, game_started, player

    sock = connection_sock
    my_id = player_id
    USERNAME = username
    game_started = True

    threading.Thread(target=listen_thread, daemon=True).start()

    # Ursina scene
    DirectionalLight(y=10, rotation=(45,-45,0))
    AmbientLight(color=color.rgba(100,100,100,0.5))
    Sky()
    Entity(model='plane', scale=200, texture='grass', texture_scale=(50,50), collider='box')

    # Generate static city and get spawn
    spawn_pos = city_generation.generate_city(tile_size=5)

    # Spawn local player safely
    player = FirstPersonController(speed=5, jump_height=2, position=spawn_pos)
    player.scale_y = 1.6
    mouse.locked = True
    mouse.visible = False

    # --- Pause menu ---
    pause_menu.setup_pause_menu()

# --- REMOTE PLAYER HANDLING ---
def create_remote(pid, pdata):
    ent = Entity(model='cube', scale=1.2, color=COLOR_MAP.get(pdata["color"], color.red))
    ent.position = Vec3(pdata["x"], pdata["y"], pdata["z"])
    label = Text(text=pdata.get("name",""), origin=(0,0), world_space=True, scale=1)
    label.position = ent.position + Vec3(0,1.2,0)
    return {"entity": ent, "label": label}

def update_remote_players():
    for pid, pdata in server_players.items():
        if pid==my_id: continue
        if pid not in other_players:
            other_players[pid] = create_remote(pid, pdata)
        else:
            other_players[pid]["entity"].position = Vec3(pdata["x"], pdata["y"], pdata["z"])
            other_players[pid]["label"].position = Vec3(pdata["x"], pdata["y"]+1.2, pdata["z"])
            other_players[pid]["label"].text = pdata.get("name","")
    for pid in list(other_players.keys()):
        if pid not in server_players:
            destroy(other_players[pid]["entity"])
            other_players[pid]["label"].enabled=False
            del other_players[pid]

def send_position():
    if player is None or sock is None:
        return
    pos = {"type": "position", "x": player.x, "y": player.y, "z": player.z}
    try:
        sock.sendall(json.dumps(pos).encode())
    except: pass


def input_handler(key):
    if not game_started: return
    pause_menu.handle_pause_input(key, game_started)


# --- UPDATE LOOP ---
def update():
    if not game_started or player is None: return
    if not pause_menu.paused:
        player.speed = 10 if held_keys["left control"] else 5
        send_position()
    update_remote_players()

def input(key):
    input_handler(key)

# --- URSINA APP INIT ---
app = Ursina(borderless=False, fullscreen=True)
menu.set_start_game_callback(start_game)
menu.create_menu()
mouse.locked = False
mouse.visible = True
app.run()
