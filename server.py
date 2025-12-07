import socket
import threading
import json
import random
import time
import os
import base64

LOCK = threading.Lock()
clients = {}        # player_id -> {"conn": conn, "addr": addr}
players = {}        # player_id -> {"x":..., "y":..., "z":..., "name":..., "color":..., "score":...}
scores = {}         # player_id -> score count
collectibles = []   # list of {"id":..., "x":..., "y":..., "z":...}
next_id = 0
next_collectible_id = 0
map_data = None     # Map file data (loaded once on server start)
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
            "collectibles": collectibles,
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
    """Load map file from assets/map directory. Returns (data, filename) or (None, None)"""
    global map_data, map_filename
    map_paths = [
        'assets/map/lesiktest.fbx',
        'map/lesiktest.fbx',
        'assets/map/lesiktest.obj',
        'map/lesiktest.obj'
    ]
    
    for path in map_paths:
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    map_data = base64.b64encode(f.read()).decode('utf-8')
                    map_filename = os.path.basename(path)
                    print(f"Loaded map file: {path} ({len(map_data)} bytes encoded)")
                    return map_data, map_filename
            except Exception as e:
                print(f"Error loading map {path}: {e}")
                continue
    
    print("WARNING: No map file found. Clients will need map files locally.")
    return None, None

def send_map_to_client(conn):
    """Send map file data to client"""
    global map_data, map_filename
    if map_data and map_filename:
        # Send map info (filename and data size)
        info_msg = json.dumps({
            "type": "map_info",
            "filename": map_filename,
            "size": len(map_data)
        }).encode()
        conn.sendall(info_msg)
        
        # Wait for client ready signal
        try:
            conn.recv(4)  # Client sends "OK"
        except:
            pass
        
        # Send base64 data in chunks
        chunk_size = 8192
        data_bytes = map_data.encode('utf-8')
        for i in range(0, len(data_bytes), chunk_size):
            chunk = data_bytes[i:i+chunk_size]
            conn.sendall(chunk)
        
        # Send completion message
        conn.sendall(json.dumps({"type": "map_complete"}).encode())
        print(f"Sent map file {map_filename} to client ({len(data_bytes)} bytes)")
    else:
        # Send empty map message
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
                if d.get("type") == "collect":
                    # Handle collectible collection
                    collectible_id = d.get("collectible_id")
                    if collectible_id:
                        # Remove collectible if it exists
                        collectibles[:] = [c for c in collectibles if c["id"] != collectible_id]
                        # Increment player score
                        if player_id not in scores:
                            scores[player_id] = 0
                        scores[player_id] += 1
                        # Spawn new collectible
                        spawn_collectible()
                elif d.get("type") == "position":
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

def spawn_collectible():
    """Spawn a new collectible. Must be called while holding LOCK."""
    global next_collectible_id
    x = random.randint(-40, 40)
    z = random.randint(-40, 40)
    y = 0.5
    collectible_id = f"c{next_collectible_id}"
    next_collectible_id += 1
    collectibles.append({"id": collectible_id, "x": x, "y": y, "z": z})

def initialize_collectibles():
    global next_collectible_id
    with LOCK:
        for i in range(30):
            spawn_collectible()  # Already inside LOCK

def start_server(port=9999):
    global next_collectible_id
    load_map_file()  # Load map on server start
    initialize_collectibles()
    
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
