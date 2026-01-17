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
ground = Entity(
    model='cube',
    scale=(50, 1, 50),
    position=(0, 0, 0),
    color=color.green,
    collider='box'
)

Sky()

# === PLAYER (IMPORTANT PART) ===
player = FirstPersonController(
    gravity=1,
    jump_height=2
)
player.collider = 'box'   # REQUIRED
player.speed = 6
player.y = 5              # spawn ABOVE map

# === NETWORK (unchanged) ===
sock = socket.socket()
sock.connect((ip, 5555))

others = {}
server_state = {}
buffer = ""

def network_thread():
    global buffer, server_state
    while True:
        data = sock.recv(4096).decode()
        if not data:
            break
        buffer += data
        while "\n" in buffer:
            raw, buffer = buffer.split("\n", 1)
            server_state = json.loads(raw)

threading.Thread(target=network_thread, daemon=True).start()

def update():
    sock.sendall((json.dumps({
        "type": "update",
        "pos": list(player.position),
        "rot": list(player.rotation)
    }) + "\n").encode())

    for pid, p in server_state.items():
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
