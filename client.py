import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from panda3d.core import loadPrcFileData
loadPrcFileData('', 'notify-level-display error')

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading, time, random
import os
import base64
import tempfile

import pause_menu
import map_loader
import gun
from enemy import Enemy
import health_bar
import respawn
import leaderboard

from server_browser import open_server_browser   # ← NEW

# --- GLOBALS ---
sock = None
USERNAME = ""
my_id = None
game_started = False
server_map_path = None  # Path to map file received from server

server_players = {}

COLOR_MAP = {
    "red": color.red, "orange": color.orange, "yellow": color.yellow,
    "green": color.green, "cyan": color.cyan, "blue": color.azure,
    "violet": color.violet, "pink": color.pink
}

player = None
other_players = {}
enemies = []  # List of enemy entities

# ----------------------------------------------------
# NETWORK LISTENER
# ----------------------------------------------------
def listen_thread():
    global server_players
    while True:
        try:
            data = sock.recv(8192)
            if not data:
                break
            msg = json.loads(data.decode())
            if msg.get("type") == "players":
                server_players = msg.get("players", {})
                # Update leaderboard data
                if "leaderboard" in msg:
                    leaderboard.update_leaderboard_data(msg.get("leaderboard", []))
        except:
            time.sleep(0.05)

# ----------------------------------------------------
# RECEIVE MAP FROM SERVER
# ----------------------------------------------------
def receive_map_from_server(sock):
    """Receive map file from server and save it temporarily"""
    global server_map_path
    try:
        # Receive map info message
        data = sock.recv(4096)
        info_msg = json.loads(data.decode())
        
        if info_msg.get("type") == "map_info":
            filename = info_msg.get("filename")
            data_size = info_msg.get("size", 0)
            
            if not filename or data_size == 0:
                print("No map file available from server")
                return None
            
            print(f"Receiving map file: {filename} ({data_size} bytes)...")
            
            # Send ready signal
            sock.sendall(b"OK")
            
            # Receive base64 data in chunks
            received = b""
            buffer = b""
            while len(received) < data_size:
                # Check if we have leftover data in buffer
                if buffer:
                    needed = data_size - len(received)
                    if len(buffer) <= needed:
                        received += buffer
                        buffer = b""
                    else:
                        received += buffer[:needed]
                        buffer = buffer[needed:]
                        break
                
                chunk = sock.recv(8192)
                if not chunk:
                    break
                
                if len(received) + len(chunk) <= data_size:
                    received += chunk
                else:
                    # Chunk contains both data and completion message
                    needed = data_size - len(received)
                    received += chunk[:needed]
                    buffer = chunk[needed:]
            
            # Check buffer for completion message
            if buffer:
                try:
                    complete_msg = json.loads(buffer.decode())
                    if complete_msg.get("type") == "map_complete":
                        pass  # Success
                except:
                    pass  # Not JSON, ignore
            
            # Decode base64 and save
            try:
                map_data = base64.b64decode(received.decode('utf-8'))
                
                # Save to temporary file
                temp_dir = os.path.join(tempfile.gettempdir(), "gtamini_maps")
                os.makedirs(temp_dir, exist_ok=True)
                server_map_path = os.path.join(temp_dir, filename)
                
                with open(server_map_path, 'wb') as f:
                    f.write(map_data)
                
                print(f"Map file saved to: {server_map_path}")
                return server_map_path
            except Exception as e:
                print(f"Error decoding map data: {e}")
                return None
        else:
            print("Unexpected message type from server")
            return None
    except Exception as e:
        print(f"Error receiving map from server: {e}")
        import traceback
        traceback.print_exc()
        return None

# ----------------------------------------------------
# CONNECT TO SERVER (used by server browser)
# ----------------------------------------------------
def connect_to_server(ip):
    global USERNAME, server_map_path
    USERNAME = f"Player{random.randint(1000,9999)}"
    picked_color = random.choice(list(COLOR_MAP.keys()))

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, 9999))

        # Receive player ID
        data = s.recv(4096)
        pid = json.loads(data.decode())["id"]
        
        # Receive map file from server
        server_map_path = receive_map_from_server(s)

        # Send info
        init = {"name": USERNAME, "color": picked_color}
        s.sendall(json.dumps(init).encode())

        return s, pid, USERNAME, picked_color
    except Exception as e:
        print("Failed connection:", e)
        import traceback
        traceback.print_exc()
        return None, None, None, None

# ----------------------------------------------------
# GAME START
# ----------------------------------------------------
def start_game(connection_sock, player_id, username, selected_color):
    global sock, my_id, USERNAME, game_started, player

    sock = connection_sock
    my_id = player_id
    USERNAME = username
    game_started = True

    threading.Thread(target=listen_thread, daemon=True).start()

    # Lighting & sky
    DirectionalLight(y=10, rotation=(45,-45,0))
    AmbientLight(color=color.rgba(100,100,100,0.5))
    Sky()

    # Load map (from server if available, otherwise local)
    forest_map = map_loader.load_map(server_map_path)

    # Player
    player = FirstPersonController(speed=5, jump_height=2, position=(0,2,0), collider='box')
    player.scale_y = 1.6
    # Ensure box collider is properly set
    if player.collider is None:
        player.collider = 'box'
    mouse.locked = True
    mouse.visible = False

    # Health bar
    health_bar.setup_health_bar(player)

    # Gun
    gun.setup_gun(player)
    
    # Spawn 5 enemies next to each other
    global enemies
    enemies = []
    base_pos = Vec3(3, 0, 10)
    for i in range(5):
        enemy = Enemy(position=base_pos + Vec3(i * 2, 0, 0), scale=(1, 2, 1))
        enemies.append(enemy)

    pause_menu.setup_pause_menu()
    
    # Leaderboard
    leaderboard.setup_leaderboard(my_id)

# ----------------------------------------------------
# SERVER BROWSER CALLBACK
# ----------------------------------------------------
def on_server_selected(ip):
    """Called when player clicks a server."""
    s, pid, username, color = connect_to_server(ip)
    if s:
        start_game(s, pid, username, color)
    else:
        print("Connection failed.")

# ----------------------------------------------------
# UPDATE LOOP
# ----------------------------------------------------
def create_remote(pid, pdata):
    ent = Entity(model='cube', scale=1.2, color=COLOR_MAP.get(pdata["color"], color.red))
    ent.position = Vec3(pdata["x"], pdata["y"], pdata["z"])
    label = Text(text=pdata.get("name",""), origin=(0,0), world_space=True, scale=1)
    label.position = ent.position + Vec3(0,1.2,0)
    return {"entity": ent, "label": label}

def update_remote_players():
    for pid, pdata in server_players.items():
        if pid == my_id: continue
        if pid not in other_players:
            other_players[pid] = create_remote(pid, pdata)
        else:
            other_players[pid]["entity"].position = Vec3(pdata["x"], pdata["y"], pdata["z"])
            other_players[pid]["label"].position = Vec3(pdata["x"], pdata["y"]+1.2, pdata["z"])
            other_players[pid]["label"].text = pdata.get("name","")
    for pid in list(other_players.keys()):
        if pid not in server_players:
            destroy(other_players[pid]["entity"])
            other_players[pid]["label"].enabled = False
            del other_players[pid]

def send_position():
    if player is None or sock is None:
        return
    pos = {"type":"position", "x":player.x, "y":player.y, "z":player.z}
    try:
        sock.sendall(json.dumps(pos).encode())
    except:
        pass

def update():
    if not game_started or player is None:
        return
    if not pause_menu.paused:
        player.speed = 10 if held_keys["left control"] else 5
        send_position()
        
        # Update enemies (hitscan shooting)
        for enemy in enemies[:]:
            if not enemy or not enemy.enabled:
                if enemy in enemies:
                    enemies.remove(enemy)
                continue
            enemy.shoot_at_player(player)
    
    update_remote_players()
    gun.update()
    respawn.update()
    leaderboard.update_leaderboard()

def input(key):
    if game_started:
        pause_menu.handle_pause_input(key, game_started)
        gun.handle_input(key)

# ----------------------------------------------------
# INIT APP
# ----------------------------------------------------
app = Ursina(fullscreen=True)

# Replace menu entirely
open_server_browser(on_server_selected)

mouse.locked = False
mouse.visible = True

app.run()
