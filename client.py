from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading, time, random

# --- CONNECT TO SERVER ---
SERVER_IP = input("Enter server IP: ").strip()
USERNAME = input("Enter your player name: ").strip() or "Player"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.connect((SERVER_IP, 9999))
except Exception as e:
    print("Could not connect:", e)
    raise SystemExit

data = sock.recv(4096).decode()
my_id = json.loads(data)["id"]
sock.sendall(json.dumps({"name": USERNAME}).encode())

server_players = {}  # player_id -> player_data

def listen_thread():
    global server_players
    while True:
        try:
            data = sock.recv(8192)
            if not data: break
            server_players = json.loads(data.decode())
        except:
            time.sleep(0.05)

threading.Thread(target=listen_thread, daemon=True).start()

# --- URSINA SETUP ---
app = Ursina()
DirectionalLight(y=10, rotation=(45,-45,0))
AmbientLight(color=color.rgba(100,100,100,0.5))
Sky()
Entity(model='plane', scale=200, texture='grass', texture_scale=(50,50), collider='box')

# PROCEDURAL CITY
for x in range(-50,51,10):
    for z in range(-50,51,10):
        if x%20==0 or z%20==0:
            Entity(
                model='cube',
                scale=(10,0.1,10),
                texture='shore',
                texture_scale=(2,2),
                color=color.rgb(180,180,180),
                position=(x,0,z),
                collider='box'
            )

building_textures = ['brick', 'white_cube', 'shore']
for i in range(50):
    x=random.randint(-50,50)
    z=random.randint(-50,50)
    h=random.randint(3,10)
    Entity(
        model='cube',
        color=color.rgb(random.randint(100,255),random.randint(100,255),random.randint(100,255)),
        texture=random.choice(building_textures),
        texture_scale=(1, h/2),
        scale=(3,h,3),
        position=(x,h/2,z),
        collider='box'
    )

# LOCAL PLAYER
player = FirstPersonController(speed=5, jump_height=2)
player.scale_y = 1.6

# REMOTE PLAYERS
other_players = {}
COLOR_MAP = {
    "red": color.red, "orange": color.orange, "yellow": color.yellow,
    "green": color.green, "cyan": color.cyan, "blue": color.blue,
    "violet": color.violet, "pink": color.pink
}

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
    pos = {"x": player.x, "y": player.y, "z": player.z}
    try:
        sock.sendall(json.dumps(pos).encode())
    except:
        pass

# COLLECTIBLES
collectibles = []
score = 0
for i in range(30):
    x=random.randint(-40,40)
    z=random.randint(-40,40)
    y=0.5
    c=Entity(model='sphere', color=color.yellow, texture='white_cube', scale=0.5, position=(x,y,z), collider='box')
    collectibles.append(c)

def check_collectibles():
    global score
    for c in collectibles:
        if player.intersects(c).hit:
            destroy(c)
            collectibles.remove(c)
            score += 1
            print("Score:", score)

# PAUSE SCREEN
paused = False
mouse.locked = True
mouse.visible = False

pause_panel = Entity(parent=camera.ui, model='quad', color=color.rgba(0,0,0,180),
                     scale=(0.7,0.4), enabled=False)
pause_label = Text("Game Paused", parent=pause_panel, y=0.15, scale=2, origin=(0,0))
pause_hint = Text("Press ESC to resume", parent=pause_panel, y=0.05, scale=1, origin=(0,0), color=color.azure)

def hide_pause_menu():
    global paused
    paused = False
    pause_panel.enabled = False
    application.paused = False
    mouse.locked = True
    mouse.visible = False

def show_pause_menu():
    global paused
    paused = True
    pause_panel.enabled = True
    application.paused = True
    mouse.locked = False
    mouse.visible = True

continue_button = Button(text="Continue", parent=pause_panel, y=-0.05, scale=(0.4,0.12))
continue_button.on_click = hide_pause_menu

exit_button = Button(text="Exit Game", parent=pause_panel, y=-0.22, scale=(0.4,0.12), color=color.red)
exit_button.on_click = application.quit

def input(key):
    if key == 'escape':
        if paused:
            hide_pause_menu()
        else:
            show_pause_menu()

# HUD
Text(text=USERNAME+" (you)", position=window.top_left+Vec2(0.06,-0.06), scale=1.2)

# UPDATE
def update():
    player.speed = 10 if held_keys["left control"] else 5
    send_position()
    update_remote_players()
    check_collectibles()

app.run()
