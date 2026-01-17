from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading

ip = input("Enter server IP: ")

app = Ursina()

window.borderless = True
window.exit_button.visible = False
window.fps_counter.enabled = True
mouse.locked = True

# === LOAD MAP (CORRECT WAY) ===
# Load the actual map file
map_model = None
try:
    map_model = Entity(
        model='assets/map/dankomapa.glb',
        position=(0, -60, 0),  # Lower the map significantly
        scale=3  # Increased map size
    )
    print("Map loaded successfully")
except Exception as e:
    print(f"Failed to load map: {e}, using fallback ground")
    map_model = None

# Add collision plane for map (invisible but provides ground collision)
# This ensures player can walk on the map surface
map_collision_plane = Entity(
    model='plane',
    scale=(200, 1, 200),
    position=(0, -60, 0),
    collider='box',
    visible=False,  # Invisible but provides collision
    enabled=(map_model is not None)  # Only enable if map loaded
)

# Fallback ground in case map doesn't load
ground = Entity(
    model='cube',
    scale=(150, 1, 150),  # Increased fallback ground size
    position=(0, -70, 0),  # Lower fallback ground to match
    color=color.green,
    collider='box',
    enabled=(map_model is None)  # Enable only if map didn't load
)

Sky()

# === PLAYER (IMPORTANT PART) ===
player = FirstPersonController(
    gravity=1,
    jump_height=2
)
player.collider = 'box'   # REQUIRED
player.speed = 6
player.y = 100             # spawn much higher above map

# Store player ID to avoid overriding own position
my_player_id = None

# === NETWORK (unchanged) ===
sock = socket.socket()
sock.connect((ip, 5555))

others = {}
server_state = {}
buffer = ""

def network_thread():
    global buffer, server_state, my_player_id
    while True:
        data = sock.recv(4096).decode()
        if not data:
            break
        buffer += data
        while "\n" in buffer:
            raw, buffer = buffer.split("\n", 1)
            server_state = json.loads(raw)
            # Set player ID on first update
            if my_player_id is None and server_state:
                # Find our player ID (the one that matches our position or is new)
                for pid in server_state.keys():
                    if pid not in others:
                        my_player_id = pid
                        break
                if my_player_id is None:
                    my_player_id = list(server_state.keys())[0] if server_state else None

threading.Thread(target=network_thread, daemon=True).start()

def update():
    # Always send updates - server will assign us an ID
    sock.sendall((json.dumps({
        "type": "update",
        "pos": list(player.position),
        "rot": list(player.rotation)
    }) + "\n").encode())

    # Update other players (but not ourselves)
    for pid, p in server_state.items():
        # Skip our own player - we control it locally
        if pid == my_player_id:
            # Only sync position if server says we're dead (for respawn)
            if not p.get("alive", True):
                respawn_pos = Vec3(*p["pos"])
                # Ensure respawn is at safe height above lowered map
                if respawn_pos.y < 40:
                    respawn_pos.y = 50
                player.position = respawn_pos
            continue
            
        if pid not in others:
            others[pid] = Entity(
                model='cube',
                color=color.red,
                scale=(.6,1.8,.6)
            )

        if p["alive"]:
            others[pid].enabled = True
            others[pid].position = lerp(
                others[pid].position,
                Vec3(*p["pos"]),
                time.dt * 10
            )
        else:
            others[pid].enabled = False

def input(key):
    if key == 'left mouse down':
        d = camera.forward
        sock.sendall((json.dumps({
            "type": "shoot",
            "origin": list(camera.world_position),
            "dir": [d.x, d.y, d.z]
        }) + "\n").encode())

app.run()
