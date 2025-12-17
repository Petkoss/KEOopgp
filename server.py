import socket
import threading
import json
import random
import time
import os

LOCK = threading.Lock()
clients = {}        # player_id -> {"conn": conn, "addr": addr}
players = {}        # player_id -> {"x":..., "y":..., "z":..., "name":..., "color":..., "score":...}
scores = {}         # player_id -> score count
next_id = 0
map_data = None     # Raw map bytes (loaded once on server start)
map_filename = None # Map filename

COLOR_POOL = [
    "red","orange","yellow","green","cyan","blue","violet","pink"
]

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def broadcast_players():
    with LOCK:
        # Include scores in player data
        players_with_scores = {}
        for pid, pdata in players.items():
            players_with_scores[pid] = pdata.copy()
            players_with_scores[pid]["score"] = scores.get(pid, 0)
        
        data = json.dumps({
            "type": "players",
            "players": players_with_scores,
            "leaderboard": sorted([(pid, players[pid]["name"], scores.get(pid, 0)) for pid in players.keys()], 
                                 key=lambda x: x[2], reverse=True)
        }).encode()
        
        removed = []
        for pid, info in clients.items():
            try:
                info["conn"].sendall(data)
            except:
                removed.append(pid)
        for r in removed:
            if r in clients: del clients[r]
            if r in players: del players[r]
            if r in scores: del scores[r]

def load_map_file():
    """Load the bundled GLB map as raw bytes. Returns (data, filename) or (None, None)."""
    global map_data, map_filename
    map_paths = [
        "assets/map/akozeke.glb",
        "map/akozeke.glb",
    ]

    for path in map_paths:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    map_data = f.read()  # raw bytes
                    map_filename = os.path.basename(path)
                    print(f"Loaded map file: {path} ({len(map_data)} bytes)")
                    return map_data, map_filename
            except Exception as e:
                print(f"Error loading map {path}: {e}")
                continue

    print("WARNING: No map file found. Clients will need map files locally.")
    return None, None

def send_map_to_client(conn):
    """Send map file data to client using raw binary."""
    global map_data, map_filename
    if map_data and map_filename:
        # Send map info (filename and raw byte size)
        info_msg = json.dumps(
            {
                "type": "map_info",
                "filename": map_filename,
                "size": len(map_data),
            }
        ).encode()
        conn.sendall(info_msg)

        # Wait for client signal: "OK" to download, "SKIP" to reuse cached copy
        try:
            signal = conn.recv(4)
        except Exception:
            signal = b""

        if signal.startswith(b"SKIP"):
            print("Client requested to skip map download (using cached copy).")
            return

        # Default behaviour: send raw bytes
        chunk_size = 8192
        total = len(map_data)
        sent = 0
        while sent < total:
            end = min(sent + chunk_size, total)
            conn.sendall(map_data[sent:end])
            sent = end

        print(f"Sent map file {map_filename} to client ({total} bytes)")
    else:
        # Send empty map message (no map on server)
        conn.sendall(json.dumps({"type": "map_info", "filename": None, "size": 0}).encode())

def handle_client(conn, addr):
    global next_id
    try:
        with LOCK:
            player_id = str(next_id)
            next_id += 1
            clients[player_id] = {"conn": conn, "addr": addr}
        conn.sendall(json.dumps({"id": player_id}).encode())
        
        # Send map file to client
        send_map_to_client(conn)

        data = conn.recv(4096)
        init = json.loads(data.decode())
        name = init.get("name", f"Player{player_id}")
        requested_color = init.get("color", "")

        with LOCK:
            # Use requested color if valid, otherwise assign from pool
            if requested_color in COLOR_POOL:
                color = requested_color
            else:
                color = COLOR_POOL[int(player_id) % len(COLOR_POOL)]
            players[player_id] = {"x":0,"y":0,"z":0,"name":name,"color":color}
            scores[player_id] = 0

        broadcast_players()

        while True:
            data = conn.recv(4096)
            if not data:
                break
            d = json.loads(data.decode())
            
            with LOCK:
                if d.get("type") == "position":
                    # Handle position update
                    if player_id in players:
                        players[player_id].update({
                            "x": float(d.get("x", players[player_id]["x"])),
                            "y": float(d.get("y", players[player_id]["y"])),
                            "z": float(d.get("z", players[player_id]["z"]))
                        })
            broadcast_players()

    except: pass
    finally:
        with LOCK:
            if player_id in clients:
                try: clients[player_id]["conn"].close()
                except: pass
                del clients[player_id]
            if player_id in players: del players[player_id]
            if player_id in scores: del scores[player_id]
        broadcast_players()

def start_server(port=9999):
    load_map_file()  # Load map on server start
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", port))
    server.listen()
    local_ip = get_local_ip()
    print(f"SERVER RUNNING ON: {local_ip}:{port}")
    print("Players on the same LAN should use this IP to connect.")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server.close()

if __name__ == "__main__":
    start_server(9999)
