import socket, threading, json, time, math, random

PORT = 5555
RESPAWN_TIME = 3
MAX_HP = 100
DAMAGE = 25
HITBOX_RADIUS = 0.6

players = {}
lock = threading.Lock()

# === GET LOCAL IP ===
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

SERVER_IP = get_local_ip()

def vec_sub(a,b): return [a[i]-b[i] for i in range(3)]
def vec_dot(a,b): return sum(a[i]*b[i] for i in range(3))

def ray_hits_sphere(origin, direction, center, radius):
    oc = vec_sub(origin, center)
    b = 2 * vec_dot(oc, direction)
    c = vec_dot(oc, oc) - radius*radius
    return (b*b - 4*c) >= 0

def respawn(pid):
    time.sleep(RESPAWN_TIME)
    with lock:
        if pid in players:
            players[pid].update({
                "hp": MAX_HP,
                "alive": True,
                "pos": [random.randint(-5,5),1,random.randint(-5,5)]
            })

def handle_client(conn, addr):
    pid = str(addr)

    with lock:
        players[pid] = {
            "pos": [0,1,0],
            "rot": [0,0,0],
            "hp": MAX_HP,
            "score": 0,
            "alive": True
        }

    buffer = ""

    try:
        while True:
            data = conn.recv(4096).decode()
            if not data:
                break
            buffer += data

            while "\n" in buffer:
                raw, buffer = buffer.split("\n", 1)
                msg = json.loads(raw)

                with lock:
                    p = players[pid]

                    if msg["type"] == "update" and p["alive"]:
                        p["pos"] = msg["pos"]
                        p["rot"] = msg["rot"]

                    elif msg["type"] == "shoot" and p["alive"]:
                        for tid, t in players.items():
                            if tid == pid or not t["alive"]:
                                continue
                            if ray_hits_sphere(
                                msg["origin"],
                                msg["dir"],
                                t["pos"],
                                HITBOX_RADIUS
                            ):
                                t["hp"] -= DAMAGE
                                if t["hp"] <= 0:
                                    t["alive"] = False
                                    p["score"] += 1
                                    threading.Thread(target=respawn, args=(tid,), daemon=True).start()

                conn.sendall((json.dumps(players) + "\n").encode())

    finally:
        with lock:
            players.pop(pid, None)
        conn.close()

def main():
    print("="*40)
    print("SERVER RUNNING")
    print(f"LAN IP: {SERVER_IP}")
    print(f"PORT  : {PORT}")
    print("="*40)

    s = socket.socket()
    s.bind(("0.0.0.0", PORT))
    s.listen()

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn,addr), daemon=True).start()

if __name__ == "__main__":
    main()
