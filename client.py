import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading, time, random
import menu

# --- GLOBALS ---
sock = None
USERNAME = ""
my_id = None
game_started = False

server_players = {}          # player_id -> player_data
server_collectibles = []     # list of collectibles from server
leaderboard = []             # list of (player_id, name, score) tuples

COLOR_MAP = {
    "red": color.red, "orange": color.orange, "yellow": color.yellow,
    "green": color.green, "cyan": color.cyan, "blue": color.azure,
    "violet": color.violet, "pink": color.pink
}

player = None
other_players = {}
collectibles = {}
collectible_entities = {}
pending_collections = set()

paused = False
pause_panel = pause_label = pause_hint = continue_button = exit_button = None
leaderboard_bg = leaderboard_title = leaderboard_text = None

spawn_position = Vec3(0, 2, 0)

# --- NETWORK LISTENER ---
def listen_thread():
    global server_players, server_collectibles, leaderboard
    while True:
        try:
            data = sock.recv(8192)
            if not data: break
            msg = json.loads(data.decode())
            if msg.get("type") == "players":
                server_players = msg.get("players", {})
                server_collectibles = msg.get("collectibles", [])
                leaderboard = msg.get("leaderboard", [])
        except:
            time.sleep(0.05)

# --- CITY GENERATION ---
def generate_city(tile_size=5):
    global spawn_position

    city_map = [
        "RRRRRRRRRRRRRRRRRRRR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RRRRRRRRRRRRRRRRRRRR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RRRRRRRRRRRRRRRRRRRR",
        "RSBBBBBPBBBBBBPBBBSR",
        "RRRRRRRRRRRRRRRRRRRR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RRRRRRRRRRRRRRRRRRRR",
    ]

    for z, row in enumerate(city_map):
        for x, cell in enumerate(row):
            world_x = x * tile_size - (len(row)*tile_size)/2
            world_z = z * tile_size - (len(city_map)*tile_size)/2

            if cell == "R":  # Road
                Entity(
                    model="cube", color=color.dark_gray,
                    scale=(tile_size, 0.1, tile_size),
                    position=(world_x, 0, world_z), collider="box"
                )

            elif cell == "B":  # Building
                # Safety: ensure building is not on road tile
                if cell == "B":
                    height = random.randint(12, 40)
                    Entity(
                        model="cube",
                        color=color.rgb(
                            random.randint(150, 255),
                            random.randint(150, 255),
                            random.randint(150, 255)
                        ),
                        scale=(tile_size*0.9, height, tile_size*0.9),
                        position=(world_x, height/2, world_z),
                        collider="box"
                    )

            elif cell == "P":  # Park
                Entity(
                    model="cube", color=color.lime.tint(-0.3),
                    scale=(tile_size, 0.2, tile_size),
                    position=(world_x, 0, world_z),
                    collider="box"
                )
                # Trees
                for i in range(random.randint(1,3)):
                    Entity(
                        model="cylinder", color=color.brown,
                        scale=(0.3,2,0.3),
                        position=(world_x + random.uniform(-1,1),
                                  1,
                                  world_z + random.uniform(-1,1))
                    )
                    Entity(
                        model="cone", color=color.green,
                        scale=(1,2,1),
                        position=(world_x + random.uniform(-1,1),
                                  2.5,
                                  world_z + random.uniform(-1,1))
                    )

            elif cell == "S":  # Player spawn
                spawn_position = Vec3(world_x, 2, world_z)

    return spawn_position

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
    spawn_pos = generate_city(tile_size=5)

    # Spawn local player safely
    player = FirstPersonController(speed=5, jump_height=2, position=spawn_pos)
    player.scale_y = 1.6
    mouse.locked = True
    mouse.visible = False

    # --- Pause menu ---
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

    # --- Leaderboard ---
    global leaderboard_bg, leaderboard_title, leaderboard_text
    leaderboard_bg = Entity(parent=camera.ui, model='quad',
                            color=color.rgba(64, 64, 64, 200),
                            scale=(0.35, 0.5), position=(-0.82, 0.4))
    leaderboard_title = Text("LEADERBOARD", parent=leaderboard_bg, y=0.45, scale=1.8,
                             origin=(0,0), color=color.black)
    leaderboard_text = Text("", parent=leaderboard_bg, y=0.25, scale=1.3, origin=(0,0),
                            color=color.black)

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

# --- COLLECTIBLES ---
def update_collectibles():
    global collectibles, collectible_entities, pending_collections
    collectible_ids_on_server = {c["id"] for c in server_collectibles}
    for cid in list(collectibles.keys()):
        if cid not in collectible_ids_on_server:
            destroy(collectibles[cid])
            del collectibles[cid]
            collectible_entities.pop(collectibles.get(cid), None)
            pending_collections.discard(cid)
    pending_collections.intersection_update(collectible_ids_on_server)
    for cdata in server_collectibles:
        cid = cdata["id"]
        if cid not in collectibles:
            c = Entity(model='sphere', color=color.yellow, texture='white_cube', scale=0.5,
                       position=(cdata["x"], cdata["y"], cdata["z"]))
            collectibles[cid] = c
            collectible_entities[c] = cid
            pending_collections.discard(cid)
    for cdata in server_collectibles:
        cid = cdata["id"]
        if cid in collectibles:
            collectibles[cid].position = Vec3(cdata["x"], cdata["y"], cdata["z"])

def check_collectibles():
    if player is None or sock is None: return
    for c in list(collectibles.values()):
        if not c.enabled: continue
        distance = (player.position - c.position).length()
        if distance < 1.5:
            cid = collectible_entities.get(c)
            if cid and cid not in pending_collections:
                try:
                    sock.sendall(json.dumps({"type": "collect", "collectible_id": cid}).encode())
                    pending_collections.add(cid)
                    c.enabled = False
                except: pass

# --- PAUSE MENU ---
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

def input_handler(key):
    if not game_started: return
    if key=='escape':
        hide_pause_menu() if paused else show_pause_menu()

# --- LEADERBOARD ---
def update_leaderboard():
    if leaderboard_text is None: return
    leaderboard_text.color = color.black
    if leaderboard_title: leaderboard_title.color = color.black
    lb_data = leaderboard if leaderboard else []
    if not lb_data and server_players:
        lb_data = [(pid, pdata.get("name","Player"), pdata.get("score",0))
                   for pid, pdata in server_players.items()]
        lb_data.sort(key=lambda x: x[2], reverse=True)
    display_text = "\n".join(
        f"{i+1}. {entry[1]}{' (you)' if str(entry[0])==str(my_id) else ''}: {entry[2]}"
        for i, entry in enumerate(lb_data[:10])
    ) if lb_data else "Waiting for players..."
    leaderboard_text.text = display_text
    leaderboard_text.color = color.black

# --- UPDATE LOOP ---
def update():
    if not game_started or player is None: return
    if not paused:
        player.speed = 10 if held_keys["left control"] else 5
        send_position()
        check_collectibles()
    update_remote_players()
    update_collectibles()
    update_leaderboard()

def input(key):
    input_handler(key)

# --- URSINA APP INIT ---
app = Ursina(borderless=False, fullscreen=True)
menu.set_start_game_callback(start_game)
menu.create_menu()
mouse.locked = False
mouse.visible = True
app.run()
