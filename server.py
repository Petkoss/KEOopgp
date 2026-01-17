import socket, threading, json, time, math, random

HOST = "0.0.0.0"
PORT = 5555

RESPAWN_TIME = 3
MAX_HP = 100
DAMAGE = 25
HITBOX_RADIUS = 0.6

players = {}
lock = threading.Lock()

def vec_sub(a,b): return [a[i]-b[i] for i in range(3)]
def vec_dot(a,b): return sum(a[i]*b[i] for i in range(3))
def vec_len(v): return math.sqrt(vec_dot(v,v))

def ray_hits_sphere(origin, direction, center, radius):
    oc = vec_sub(origin, center)
    b = 2 * vec_dot(oc, direction)
    c = vec_dot(oc, oc) - radius*radius
    disc = b*b - 4*c
    return disc >= 0

def handle_client(conn, addr):
    pid = str(addr)
    with lock:
        players[pid] = {
            "pos": [random.randint(-5,5),1,random.randint(-5,5)],
            "rot": [0,0,0],
            "hp": MAX_HP,
            "score": 0,
            "alive": True
        }

    try:
        while True:
            data = conn.recv(8192)
            if not data:
                break
            msg = json.loads(data.decode())

            with lock:
                p = players[pid]

                if msg["type"] == "update":
                    if p["alive"]:
                        p["pos"] = msg["pos"]
                        p["rot"] = msg["rot"]

                elif msg["type"] == "shoot" and p["alive"]:
                    origin = msg["origin"]
                    direction = msg["dir"]

                    for tid, target in players.items():
                        if tid == pid or not target["alive"]:
                            continue

                        if ray_hits_sphere(origin, direction, target["pos"], HITBOX_RADIUS):
                            target["hp"] -= DAMAGE
                            if target["hp"] <= 0:
                                target["alive"] = False
                                p["score"] += 1
                                threading.Thread(
                                    target=respawn_player,
                                    args=(tid,),
                                    daemon=True
                                ).start()

            conn.sendall(json.dumps(players).encode())

    finally:
        with lock:
            if pid in players:
                del players[pid]
        conn.close()

def respawn_player(pid):
    time.sleep(RESPAWN_TIME)
    with lock:
        if pid in players:
            players[pid].update({
                "hp": MAX_HP,
                "alive": True,
                "pos": [random.randint(-5,5),1,random.randint(-5,5)]
            })

def main():
    s = socket.socket()
    s.bind((HOST, PORT))
    s.listen()
    print("Server running on port", PORT)

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn,addr), daemon=True).start()

if __name__ == "__main__":
    main()
