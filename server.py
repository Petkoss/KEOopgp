import socket
import threading
import json
import random
import time
import os
import killtrack

LOCK = threading.Lock()
clients = {}        # player_id -> {"conn": conn, "addr": addr}
players = {}        # player_id -> {"x":..., "y":..., "z":..., "name":..., "color":..., "health":...}
health = {}         # player_id -> current health value
MAX_HEALTH = 100
next_id = 0
map_data = None     # Raw map bytes (loaded once on server start)
map_filename = None # Map filename

# Broadcast throttling
last_broadcast_time = {}
broadcast_interval = 0.1  # Broadcast every 100ms (10 times per second instead of 60+)
periodic_broadcast_interval = 0.5  # Periodic broadcast every 500ms to keep leaderboard fresh
last_periodic_broadcast = 0

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
    """Broadcast player data including kills/points to all clients"""
    with LOCK:
        # Include kills and health in player data
        # Get all tracked kills once for efficiency
        all_tracked_kills = killtrack.get_all_kills()
        players_with_data = {}
        for pid, pdata in players.items():
            players_with_data[pid] = pdata.copy()
            # Ensure kills are tracked - initialize if not already done
            if pid not in all_tracked_kills:
                killtrack.initialize_player(pid)
                all_tracked_kills[pid] = 0  # Update local copy
            # Always include kills/points, default to 0 if missing
            players_with_data[pid]["kills"] = killtrack.get_kills(pid)
            players_with_data[pid]["health"] = health.get(pid, MAX_HEALTH)
            players_with_data[pid]["max_health"] = MAX_HEALTH
        
        # Generate leaderboard using killtrack module (for reference, clients use players_with_data)
        leaderboard = killtrack.get_leaderboard(players)
        
        data = json.dumps({
            "type": "players",
            "players": players_with_data,  # This contains all player data including kills
            "leaderboard": leaderboard
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
            if r in health: del health[r]
            killtrack.remove_player(r)  # Clean up kill tracking

def load_map_file():
    """Load the bundled GLB map as raw bytes. Returns (data, filename) or (None, None)."""
    global map_data, map_filename
    map_paths = [
        "assets/map/maleakozeke.glb",
        "map/maleakozeke.glb",
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
            health[player_id] = MAX_HEALTH  # Initialize health
            killtrack.initialize_player(player_id)  # Initialize kill tracking

        broadcast_players()

        while True:
            data = conn.recv(4096)
            if not data:
                break
            d = json.loads(data.decode())
            
            should_broadcast = False
            with LOCK:
                if d.get("type") == "position":
                    # Handle position update
                    if player_id in players:
                        players[player_id].update({
                            "x": float(d.get("x", players[player_id]["x"])),
                            "y": float(d.get("y", players[player_id]["y"])),
                            "z": float(d.get("z", players[player_id]["z"]))
                        })
                    # Throttle position broadcasts - only broadcast if enough time has passed
                    current_time = time.time()
                    if current_time - last_broadcast_time.get("position", 0) >= broadcast_interval:
                        last_broadcast_time["position"] = current_time
                        should_broadcast = True
                elif d.get("type") == "damage":
                    # Handle damage event
                    target_id = d.get("target_id")
                    damage_amount = float(d.get("amount", 0))
                    attacker_id = player_id
                    
                    # Validate: can't damage yourself, target must exist, attacker must exist
                    if (target_id and target_id != attacker_id and 
                        target_id in players and target_id in health and
                        attacker_id in players):
                        # Apply damage
                        health[target_id] = max(0, health[target_id] - damage_amount)
                        
                        # Award kill to attacker if target dies
                        if health[target_id] <= 0 and target_id in health:
                            killtrack.award_kill(attacker_id, target_id)
                            # Reset target health after death (respawn)
                            health[target_id] = MAX_HEALTH
                        
                        # Damage events should broadcast immediately
                        should_broadcast = True
            
            # Broadcast if needed
            if should_broadcast:
                broadcast_players()

    except: pass
    finally:
        with LOCK:
            if player_id in clients:
                try: clients[player_id]["conn"].close()
                except: pass
                del clients[player_id]
            if player_id in players: del players[player_id]
            if player_id in health: del health[player_id]
            killtrack.remove_player(player_id)  # Clean up kill tracking
        broadcast_players()

def periodic_broadcast_loop():
    """Periodically broadcast player data to keep leaderboard fresh"""
    global last_periodic_broadcast
    while True:
        try:
            current_time = time.time()
            # Broadcast every 500ms if there are clients connected
            # broadcast_players() has its own lock, so no need to lock here
            if current_time - last_periodic_broadcast >= periodic_broadcast_interval:
                with LOCK:
                    has_clients = len(clients) > 0
                if has_clients:  # Only broadcast if there are connected clients
                    broadcast_players()
                last_periodic_broadcast = current_time
            time.sleep(0.1)  # Check every 100ms
        except:
            time.sleep(0.5)

def start_server(port=9999):
    load_map_file()  # Load map on server start
    
    # Start periodic broadcast thread to keep leaderboard data fresh
    threading.Thread(target=periodic_broadcast_loop, daemon=True).start()
    
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
