import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from panda3d.core import loadPrcFileData
loadPrcFileData('', 'notify-level-display error')

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading, time, random
import os
import tempfile

import pause_menu
import map_loader
import gun
from enemy import Enemy
import health_bar
import respawn
import leaderboard
import player as player_mod

from server_browser import open_server_browser, get_current_browser

# --- GLOBALS ---
sock = None
USERNAME = ""
my_id = None
game_started = False
server_map_path = None  # Path to map file received from server

server_players = {}
last_position_send = 0
position_send_interval = 0.05  # Send position every 50ms (20 times per second instead of 60+)

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
                if "leaderboard" in msg:
                    leaderboard.update_leaderboard_data(msg.get("leaderboard", []))
        except:
            time.sleep(0.05)


# ----------------------------------------------------
# RECEIVE MAP FROM SERVER
# ----------------------------------------------------
def receive_map_from_server(sock, initial_buffer: bytes = b""):
    """Receive map file from server and save it temporarily (raw binary with caching)."""
    global server_map_path
    try:
        # First message: map_info JSON (môže byť nalepený na ďalšie dáta)
        if initial_buffer:
            data = initial_buffer
        else:
            data = sock.recv(4096)

        raw = data.decode()
        end_idx = raw.find("}")
        if end_idx == -1:
            info_msg = json.loads(raw)
        else:
            info_part = raw[: end_idx + 1]
            info_msg = json.loads(info_part)

        if info_msg.get("type") != "map_info":
            print("Unexpected message type from server (expected map_info)")
            return None

        filename = info_msg.get("filename")
        data_size = info_msg.get("size", 0)

        if not filename or data_size == 0:
            print("No map file available from server")
            return None

        temp_dir = os.path.join(tempfile.gettempdir(), "gtamini_maps")
        os.makedirs(temp_dir, exist_ok=True)
        cached_path = os.path.join(temp_dir, filename)

        # If we already have the file with the same size, reuse it and ask server to skip
        if os.path.exists(cached_path) and os.path.getsize(cached_path) == data_size:
            print(f"Using cached map file at {cached_path}, skipping download.")
            try:
                sock.sendall(b"SKIP")
            except Exception:
                pass
            server_map_path = cached_path
            return server_map_path

        print(f"Receiving map file: {filename} ({data_size} bytes)...")

        # Tell server we are ready to receive raw bytes
        sock.sendall(b"OK")

        # Receive raw binary data and write directly to file
        bytes_remaining = data_size
        server_map_path = cached_path
        with open(server_map_path, "wb") as f:
            while bytes_remaining > 0:
                chunk_size = min(8192, bytes_remaining)
                try:
                    chunk = sock.recv(chunk_size)
                except socket.timeout:
                    print("Timed out while receiving map data from server")
                    return None

                if not chunk:
                    print("Connection closed before full map was received.")
                    return None

                f.write(chunk)
                bytes_remaining -= len(chunk)

        print(f"Map file saved to: {server_map_path}")
        return server_map_path

    except Exception as e:
        print(f"Error receiving map from server: {e}")
        import traceback
        traceback.print_exc()
        return None


# ----------------------------------------------------
# CONNECT TO SERVER (used by server browser)
# ----------------------------------------------------
def connect_to_server(ip, username=None):
    global USERNAME, server_map_path
    if username and username.strip():
        USERNAME = username.strip()
    else:
        USERNAME = f"Player{random.randint(1000,9999)}"
    picked_color = random.choice(list(COLOR_MAP.keys()))

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((ip, 9999))

        # First message: player id JSON, ale môže byť nalepený na map_info
        data = s.recv(4096)
        raw = data.decode()

        leftover_bytes = b""
        try:
            pid = json.loads(raw)["id"]
        except json.JSONDecodeError:
            end_idx = raw.find("}")
            if end_idx == -1:
                raise
            first_obj = raw[: end_idx + 1]
            rest = raw[end_idx + 1 :]
            pid = json.loads(first_obj)["id"]
            leftover_bytes = rest.encode() if rest else b""

        # Receive map file from server (príp. so zvyškom z prvého recv)
        server_map_path = receive_map_from_server(s, initial_buffer=leftover_bytes)

        # Send init info
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

    # Ensure server browser is completely hidden/destroyed
    browser = get_current_browser()
    if browser:
        try:
            if hasattr(browser, '_cleanup_ui'):
                browser._cleanup_ui()
            destroy(browser)
        except:
            pass
    
    # Also hide any remaining UI elements that might be parented to camera.ui
    # This is a safety measure in case cleanup didn't catch everything
    try:
        for child in list(camera.ui.children):
            # Check if it's a server browser UI element (buttons, text, panels, etc.)
            if hasattr(child, 'text') and child.text and (
                "KOŠICE ONLINE SERVERY" in child.text or 
                "Searching for LAN servers" in child.text or
                "Server nenájdený" in child.text or
                "Kliknite server" in child.text or
                "Hľadám servery" in child.text
            ):
                destroy(child)
            elif hasattr(child, 'text') and child.text and ":" in child.text and child.text.replace(".", "").replace(":", "").isdigit():
                # Likely a server IP button
                destroy(child)
    except:
        pass

    threading.Thread(target=listen_thread, daemon=True).start()

    # Zvyšok je pôvodný setup scény a hráča
    # Lighting & sky (bez tieňov kvôli výkonu)
    DirectionalLight(y=10, rotation=(45, -45, 0), shadows=False)
    AmbientLight(color=color.rgba(100, 100, 100, 0.5))
    Sky()

    # Load map (from server if available, otherwise local)
    try:
        forest_map = map_loader.load_map(server_map_path)
        if forest_map is None:
            print("WARNING: Map failed to load, continuing without map...")
    except Exception as e:
        print(f"ERROR: Failed to load map: {e}")
        import traceback
        traceback.print_exc()
        print("Continuing without map...")

    # Pause menu UI
    pause_menu.setup_pause_menu()

    # Leaderboard UI
    leaderboard.setup_leaderboard(my_id)

    # Player – posuň spawn trochu vyššie a dozadu, aby nebol vnútri budovy
    player = player_mod.setup_local_player(
        position=Vec3(0, 4, -20),
        normal_speed=5,
        sprint_speed=10,
        jump_height=2,
    )

    # Health bar
    health_bar.setup_health_bar(player)

    # Gun
    gun.setup_gun(player)

    # Enemies - dočasne vypnuté
    global enemies
    enemies = []
    # base_pos = Vec3(3, 0, 10)
    # for i in range(5):
    #     enemy = Enemy(position=base_pos + Vec3(i * 2, 0, 0), scale=(1, 2, 1))
    #     enemies.append(enemy)

    # Stále môžeme nechať statický playermodel ako dekoráciu, ale posuň ho ďalej od spawnu
    base_pos = Vec3(5, 0, 5)
    player_mod.spawn_static_playermodel(position=base_pos, scale=1.2)


# ----------------------------------------------------
# SERVER BROWSER CALLBACK
# ----------------------------------------------------
def on_server_selected(ip, username=None):
    """Called when player clicks a server."""

    # Žiadny loading screen – len log do konzoly
    print(f"Connecting to server {ip}...")

    def _connect():
        try:
            # Use the username parameter from outer scope
            player_username = username
            s, pid, player_username, color = connect_to_server(ip, player_username)
            if s:
                # Run start_game on the main thread
                from ursina import invoke
                invoke(lambda: start_game(s, pid, player_username, color))
            else:
                print("Connection failed.")
                from ursina import invoke
                invoke(lambda: open_server_browser(on_server_selected))
        except Exception as e:
            print(f"Unexpected error in _connect: {e}")
            import traceback
            traceback.print_exc()
            from ursina import invoke
            invoke(lambda: open_server_browser(on_server_selected))

    threading.Thread(target=_connect, daemon=True).start()


# ----------------------------------------------------
# UPDATE LOOP
# ----------------------------------------------------
def create_remote(pid, pdata):
    ent = Entity(model="cube", scale=1.2, color=COLOR_MAP.get(pdata["color"], color.red), collider="box")
    ent.position = Vec3(pdata["x"], pdata["y"], pdata["z"])
    # Store player_id on entity for damage identification
    ent.player_id = pid
    # Make remote players damageable
    player_mod._attach_health(ent)
    # Initialize health from server data
    ent.health = pdata.get("health", 100)
    ent.max_health = pdata.get("max_health", 100)
    label = Text(text=pdata.get("name", ""), origin=(0, 0), world_space=True, scale=1)
    label.position = ent.position + Vec3(0, 1.2, 0)
    return {"entity": ent, "label": label}


def update_remote_players():
    for pid, pdata in server_players.items():
        if pid == my_id:
            continue
        if pid not in other_players:
            other_players[pid] = create_remote(pid, pdata)
        else:
            other_players[pid]["entity"].position = Vec3(pdata["x"], pdata["y"], pdata["z"])
            other_players[pid]["label"].position = Vec3(pdata["x"], pdata["y"] + 1.2, pdata["z"])
            other_players[pid]["label"].text = pdata.get("name", "")
            # Update health from server
            if hasattr(other_players[pid]["entity"], "health"):
                other_players[pid]["entity"].health = pdata.get("health", 100)
                other_players[pid]["entity"].max_health = pdata.get("max_health", 100)
    for pid in list(other_players.keys()):
        if pid not in server_players:
            destroy(other_players[pid]["entity"])
            other_players[pid]["label"].enabled = False
            del other_players[pid]


def send_position():
    global last_position_send
    if player is None or sock is None:
        return
    # Throttle position updates to reduce network traffic
    current_time = time.time()
    if current_time - last_position_send < position_send_interval:
        return
    last_position_send = current_time
    pos = {"type": "position", "x": player.x, "y": player.y, "z": player.z}
    try:
        sock.sendall(json.dumps(pos).encode())
    except:
        pass


def update():
    if not game_started or player is None:
        return
    if not pause_menu.paused:
        send_position()
        player_mod.update_local_player(player)
        
        # Sync local player health from server (server is authoritative)
        # Only update if health actually changed to avoid unnecessary updates
        if my_id and my_id in server_players:
            server_health = server_players[my_id].get("health", 100)
            if hasattr(player, "health") and abs(player.health - server_health) > 0.1:
                player.health = server_health
                if health_bar.player_health != server_health:
                    health_bar.player_health = server_health
                    health_bar.update_health_bar()

        # Enemies sú vypnuté, takže netreba ich updateovať
        # for enemy in enemies[:]:
        #     if not enemy or not enemy.enabled:
        #         if enemy in enemies:
        #             enemies.remove(enemy)
        #         continue
        #     enemy.shoot_at_player(player)

    update_remote_players()
    gun.update()
    respawn.update()
    # Only update leaderboard when visible (TAB is held)
    if held_keys.get('tab'):
        leaderboard.update_visibility()
        leaderboard.update_leaderboard()
    else:
        leaderboard.update_visibility()  # Still need to check visibility to hide it


def input(key):
    if game_started:
        pause_menu.handle_pause_input(key, game_started)
        gun.handle_input(key)


# ----------------------------------------------------
# INIT APP
# ----------------------------------------------------
app = Ursina(fullscreen=True)

open_server_browser(on_server_selected)

mouse.locked = False
mouse.visible = True

app.run()
