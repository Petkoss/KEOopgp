from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading, time

app = Ursina()
window.borderless = False

ip = input("Server IP: ")
sock = socket.socket()
sock.connect((ip, 5555))

player = FirstPersonController()
player.cursor.visible = False
player.speed = 6

others = {}
scores = {}

leaderboard = Text(
    origin=(.5,.5),
    position=(.85,.45),
    scale=1.2
)

def network():
    while True:
        data = sock.recv(8192)
        if not data:
            break
        state = json.loads(data.decode())

        for pid, p in state.items():
            scores[pid] = p["score"]

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

threading.Thread(target=network, daemon=True).start()

def update():
    sock.sendall(json.dumps({
        "type": "update",
        "pos": list(player.position),
        "rot": list(player.rotation)
    }).encode())

    leaderboard.text = "\n".join(
        [f"{k[-5:]} : {v}" for k,v in scores.items()]
    )

def input(key):
    if key == 'left mouse down':
        dir = camera.forward
        sock.sendall(json.dumps({
            "type": "shoot",
            "origin": list(camera.world_position),
            "dir": [dir.x, dir.y, dir.z]
        }).encode())

Sky()
app.run()
