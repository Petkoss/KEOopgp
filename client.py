import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from panda3d.core import loadPrcFileData
loadPrcFileData('', 'notify-level-display error')

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, json, threading, time, random
import os
import tempfile

# ----------------------------
# PATCH TEXTFIELD TO FIX _active ATTRIBUTE ERROR
# ----------------------------
def patch_textfield_class():
    """
    Monkey-patch TextField class to ensure _active attribute always exists.
    This prevents AttributeError when Ursina tries to access _active before it's initialized.
    """
    try:
        from ursina.prefabs.text_field import TextField
        def safe_active_getter(self):
            """Safe getter for active property that initializes _active if needed."""
            if not hasattr(self, '__dict__') or '_active' not in self.__dict__:
                object.__setattr__(self, '_active', False)
            return self.__dict__.get('_active', False)
        
        def safe_active_setter(self, value):
            """Safe setter for active property."""
            object.__setattr__(self, '_active', bool(value))
        
        # Replace the property with our safe version
        TextField.active = property(safe_active_getter, safe_active_setter)
    except Exception:
        # Silently fail if patching doesn't work
        pass

# Apply patch early, before any TextField objects are created
patch_textfield_class()

import pause_menu
import map_loader
import gun
from enemy import Enemy
import health_bar
import respawn
import leaderboard
import player as player_mod
import playermodel

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
    recv_buf = b""
    while True:
        try:
            data = sock.recv(8192)
            if not data:
                break
            recv_buf += data
            while b"\n" in recv_buf:
                line, recv_buf = recv_buf.split(b"\n", 1)
                if not line.strip():
                    continue
                msg = json.loads(line.decode())
            if msg.get("type") == "players":
                server_players = msg.get("players", {})
                # Update leaderboard with player data
                leaderboard.update_leaderboard_data(server_players)
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
        s.sendall(json.dumps(init).encode() + b"\n")

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

    # First, ensure all InputFields are disabled and fixed to prevent TextField crashes
    try:
        from ursina import scene
        # Fix all InputFields in the scene before starting game
        if hasattr(scene, 'entities'):
            for ent in list(scene.entities):
                try:
                    if hasattr(ent, '__class__') and 'InputField' in str(type(ent)):
                        ent.enabled = False
                        if hasattr(ent, 'text_field') and ent.text_field:
                            tf = ent.text_field
                            # Safely initialize _active attribute without triggering property getter
                            try:
                                # Always use object.__setattr__ to avoid triggering property getter/setter
                                object.__setattr__(tf, '_active', False)
                                tf.enabled = False
                            except (AttributeError, KeyError):
                                pass
                except:
                    pass
    except:
        pass

    # Ensure server browser is completely hidden/destroyed
    browser = get_current_browser()
    if browser:
        try:
            # First, properly clean up InputField objects to prevent TextField crashes
            if hasattr(browser, 'name_input') and browser.name_input:
                try:
                    # Disable and fix TextField before destroying
                    browser.name_input.enabled = False
                    if hasattr(browser.name_input, 'text_field') and browser.name_input.text_field:
                        tf = browser.name_input.text_field
                        # Safely initialize _active attribute without triggering property getter
                        try:
                            if not hasattr(tf, '__dict__') or '_active' not in tf.__dict__:
                                object.__setattr__(tf, '_active', False)
                            else:
                                tf._active = False
                            tf.enabled = False
                        except (AttributeError, KeyError):
                            pass
                    # Remove from scene before destroying
                    if hasattr(browser.name_input, 'remove_node'):
                        browser.name_input.remove_node()
                except Exception as e:
                    print(f"Error cleaning up InputField: {e}")
            
            # Clean up all UI elements first
            if hasattr(browser, '_cleanup_ui'):
                browser._cleanup_ui()
            if hasattr(browser, '_ui_elems'):
                for ent in list(browser._ui_elems):
                    try:
                        # Properly disable InputFields before destroying
                        if hasattr(ent, '__class__') and 'InputField' in str(type(ent)):
                            ent.enabled = False
                            if hasattr(ent, 'text_field') and ent.text_field:
                                tf = ent.text_field
                                # Safely initialize _active attribute without triggering property getter
                                try:
                                    if not hasattr(tf, '__dict__') or '_active' not in tf.__dict__:
                                        object.__setattr__(tf, '_active', False)
                                    else:
                                        tf._active = False
                                    tf.enabled = False
                                except (AttributeError, KeyError):
                                    pass
                        destroy(ent)
                    except:
                        pass
            if hasattr(browser, 'buttons'):
                for btn in list(browser.buttons):
                    try:
                        destroy(btn)
                    except:
                        pass
            # Destroy all children
            if hasattr(browser, 'children'):
                for child in list(browser.children):
                    try:
                        destroy(child)
                    except:
                        pass
            # Finally destroy the browser entity itself
            destroy(browser)
        except Exception as e:
            print(f"Error cleaning up server browser: {e}")
    
    # Also clean up any remaining server browser UI elements from camera.ui
    # This is a thorough cleanup in case anything was missed
    try:
        cleanup_attempts = 0
        max_attempts = 3
        while cleanup_attempts < max_attempts:
            found_any = False
            for child in list(camera.ui.children):
                try:
                    should_destroy = False
                    # Check if it's an InputField and properly clean it up
                    if hasattr(child, '__class__') and 'InputField' in str(type(child)):
                        should_destroy = True
                        # Fix TextField before destroying
                        child.enabled = False
                        if hasattr(child, 'text_field') and child.text_field:
                            tf = child.text_field
                            # Safely initialize _active attribute without triggering property getter
                            try:
                                # Always use object.__setattr__ to avoid triggering property getter/setter
                                object.__setattr__(tf, '_active', False)
                                tf.enabled = False
                            except (AttributeError, KeyError):
                                pass
                    else:
                        # Check if it's a server browser UI element
                        if hasattr(child, 'text') and child.text:
                            text_lower = child.text.lower()
                            if any(keyword in text_lower for keyword in [
                                "košice online servery", "searching for lan servers",
                                "server nenájdený", "kliknite server", "hľadám servery",
                                "zadaj meno", "refresh"
                            ]):
                                should_destroy = True
                            elif ":" in child.text and len(child.text.split(":")) == 2:
                                # Likely a server IP:PORT button
                                parts = child.text.replace(":", " ").split()
                                if len(parts) == 2 and all(p.replace(".", "").isdigit() for p in parts):
                                    should_destroy = True
                        
                        # Also check if it's a Panel with dark background (server browser background)
                        if hasattr(child, 'model') and hasattr(child, 'color'):
                            if child.model == 'quad' and hasattr(child.color, 'a') and child.color.a > 0.5:
                                # Could be server browser background panel
                                if hasattr(child, 'scale') and child.scale_x > 10 and child.scale_y > 8:
                                    should_destroy = True
                    
                    if should_destroy:
                        destroy(child)
                        found_any = True
                except:
                    pass
            
            if not found_any:
                break
            cleanup_attempts += 1
            
            # No delay needed - cleanup loop will naturally exit when no entities found
    except Exception as e:
        print(f"Error in secondary server browser cleanup: {e}")

    threading.Thread(target=listen_thread, daemon=True).start()

    # Zvyšok je pôvodný setup scény a hráča
    # Lighting & sky (bez tieňov kvôli výkonu)
    DirectionalLight(y=10, rotation=(45, -45, 0), shadows=False)
    AmbientLight(color=color.rgba(100, 100, 100, 0.5))
    Sky()

    # Load map using map_loader (use server's map if available, otherwise use default shooting_game_environment_map_tdm.glb)
    try:
        # Use server's map if available, otherwise use default
        map_path = server_map_path if server_map_path and os.path.exists(server_map_path) else None
        forest_map = map_loader.load_map(map_path)
        if forest_map is None:
            print("WARNING: Map failed to load, continuing without map...")
    except Exception as e:
        print(f"ERROR: Failed to load map: {e}")
        import traceback
        traceback.print_exc()
        print("Continuing without map...")

    # Pause menu UI
    pause_menu.setup_pause_menu()

    # Leaderboard UI (fullscreen, shown when TAB is held)
    leaderboard.setup_leaderboard(my_id)

    # Player – spawn in the middle of the floor block
    # Floor top is at y=0, spawn player slightly above ground at center
    # Ensure mouse is locked before creating player controller
    mouse.locked = True
    mouse.visible = False
    player = player_mod.setup_local_player(
        position=Vec3(0, 10, 0),  # Spawn higher to avoid getting stuck in geometry (y=10)
        normal_speed=5,
        sprint_speed=10,
        jump_height=2,
    )
    # Ensure player controller is enabled and properly initialized
    if hasattr(player, 'enabled'):
        player.enabled = True
    # Ensure speed is set correctly
    if hasattr(player, 'speed'):
        player.speed = player.normal_speed
    # Set player reference for respawn system
    respawn.set_player(player)

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

    # Spawn static playermodel on the floor block (taller than before)
    # Store it globally so we can reference it
    global static_test_player
    base_pos = Vec3(5, 0, 5)  # Position on top of floor block (y=0 is top of block)
    # Spawn white cube with 100 health - it will be destroyed after 5 shots (20 damage each)
    static_test_player = player_mod.spawn_static_playermodel(position=base_pos, scale=2.0, max_health=100)


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
    """Create remote player entity for given pid if it doesn't already exist.
    If it exists, just return the existing one to avoid spawning duplicates.
    """
    # Normalize pid to string to keep keys consistent with JSON player ids
    pid = str(pid)

    # If we already have an entity for this pid, reuse it instead of creating a new one
    if pid in other_players and other_players[pid].get("entity"):
        return other_players[pid]

    # Use playermodel module to load the actual player model (GLB file)
    ent = None
    try:
        # Use playermodel.spawn_static_playermodel to load the GLB model
        # Note: playermodel uses scale=(scale, scale * 5, scale), so with scale=1.2, height = 6.0
        # Server y position is typically player center, so we need to adjust for model height
        playermodel_scale = 1.2
        playermodel_height = playermodel_scale * 5  # Height from scale y component
        # Position the model so its center is at the player position
        model_position = Vec3(pdata["x"], pdata["y"], pdata["z"])
        
        ent = playermodel.spawn_static_playermodel(
            position=model_position,
            scale=playermodel_scale,
            model_path='assets/john_wick_fortnite.glb'
        )
        
        # Apply color tint to the model
        if ent:
            player_color = COLOR_MAP.get(pdata["color"], color.red)
            if hasattr(ent, 'color'):
                ent.color = player_color
            # Adjust position if needed (model center should match player center)
            ent.position = model_position
            
            # Ensure collider is properly set up for raycast detection
            if not ent.collider:
                ent.collider = "box"
            
            # Ensure collider is enabled for raycast
            try:
                if hasattr(ent, 'collider') and ent.collider:
                    if hasattr(ent.collider, 'enabled'):
                        ent.collider.enabled = True
            except:
                pass
            
            # Increase collider size for easier hits - override scale if needed for hitbox
            if hasattr(ent, 'scale'):
                # Make width/depth larger (0.8 instead of model default)
                ent.scale_x = max(ent.scale_x, 0.8)
                ent.scale_z = max(ent.scale_z, 0.8)
    except Exception as e:
        print(f"Warning: Could not load playermodel for remote player {pid}: {e}")
        # Fallback to cube if model loading fails
        # Server y position is player center, so use it directly
        # Use larger dimensions for easier hits
        cube_height = 2.4
        cube_width_depth = 0.8  # Increased from 0.3 for larger hitbox
        
        ent = Entity(
            model="cube",
            scale=(cube_width_depth, cube_height, cube_width_depth),
            color=COLOR_MAP.get(pdata["color"], color.red),
            collider="box"
        )
        ent.position = Vec3(pdata["x"], pdata["y"], pdata["z"])
        # Mark as player target immediately
        ent.is_player_target = True
        print(f"[CREATE_REMOTE] Created fallback cube for player {pid} at {ent.position}")
    
    if not ent:
        # Ultimate fallback - create a simple cube with larger hitbox
        cube_height = 2.4
        cube_width_depth = 0.8  # Increased from 0.3 for larger hitbox
        ent = Entity(
            model="cube",
            scale=(cube_width_depth, cube_height, cube_width_depth),
            color=COLOR_MAP.get(pdata["color"], color.red),
            collider="box"
        )
        ent.position = Vec3(pdata["x"], pdata["y"], pdata["z"])
        # Mark as player target immediately
        ent.is_player_target = True
        print(f"[CREATE_REMOTE] Created ultimate fallback cube for player {pid} at {ent.position}")
    
    # Ensure entity has a collider for raycast detection (critical for hit detection)
    if not hasattr(ent, 'collider') or not ent.collider:
        ent.collider = "box"
    
    # Ensure collider is enabled for raycast detection
    try:
        if hasattr(ent, 'collider') and ent.collider:
            if hasattr(ent.collider, 'enabled'):
                ent.collider.enabled = True
    except:
        pass
    
    # Store player_id on entity for damage identification
    ent.player_id = pid
    
    # Mark entity as player target so it can be detected by gun system
    ent.is_player_target = True
    
    # Make remote players damageable (client-side health management)
    player_mod._attach_health(ent)
    # Health is managed purely on client side - start at full health
    ent.health = 100
    ent.max_health = 100
    
    # Debug: Print entity properties to verify setup
    print(f"[CREATE_REMOTE] Created player entity {pid}: player_id={ent.player_id}, is_player_target={ent.is_player_target}, has_collider={hasattr(ent, 'collider') and ent.collider is not None}, position={ent.position}")
    
    # Calculate label position based on entity height
    # Try to get the height from the entity's scale
    if hasattr(ent, 'scale') and len(ent.scale) >= 2:
        entity_height = ent.scale[1]
    else:
        entity_height = 2.4 * 1.2  # Default height
    
    # Position label above the player model (at player y position + half height + offset)
    label = Text(text=pdata.get("name", ""), origin=(0, 0), world_space=True, scale=1)
    label.position = Vec3(pdata["x"], pdata["y"] + entity_height / 2 + 0.5, pdata["z"])
    
    # Disable Text label from raycast detection - it should not block hits
    try:
        if hasattr(label, 'collider'):
            label.collider = None
        if hasattr(label, 'nodePath') and label.nodePath:
            label.nodePath.setCollideMask(0)
    except:
        pass
    
    # Store and return the remote player record
    other_players[pid] = {"entity": ent, "label": label}
    return other_players[pid]


def update_remote_players():
    # Normalize server player ids to strings to match other_players keys
    for raw_pid, pdata in server_players.items():
        pid = str(raw_pid)
        if pid == my_id:
            continue
        if pid not in other_players:
            other_players[pid] = create_remote(pid, pdata)
        else:
            # Update position - server y position is player center, so use it directly
            ent = other_players[pid]["entity"]
            label = other_players[pid].get("label")
            
            # Check if entity still exists and is valid before updating position
            if not ent or not hasattr(ent, 'nodePath') or not ent.nodePath or ent.nodePath.isEmpty():
                # Entity was destroyed, recreate it
                other_players[pid] = create_remote(pid, pdata)
                continue
            
            try:
                ent.position = Vec3(pdata["x"], pdata["y"], pdata["z"])
            except (AssertionError, AttributeError) as e:
                # Entity was destroyed, recreate it
                print(f"Entity for player {pid} was destroyed, recreating: {e}")
                other_players[pid] = create_remote(pid, pdata)
                continue
            
            # Update rotation (yaw angle for horizontal rotation)
            rotation_y = pdata.get("rotation_y", 0)
            try:
                # Ursina entities use rotation as Vec3 (x, y, z)
                # rotation_y is the horizontal rotation (yaw)
                # Keep existing x and z rotation, only update y (horizontal)
                current_rot = getattr(ent, 'rotation', Vec3(0, 0, 0))
                if isinstance(current_rot, (tuple, list)) and len(current_rot) >= 3:
                    ent.rotation = Vec3(current_rot[0], rotation_y, current_rot[2])
                elif hasattr(current_rot, 'x') and hasattr(current_rot, 'z'):
                    ent.rotation = Vec3(current_rot.x, rotation_y, current_rot.z)
                else:
                    ent.rotation = Vec3(0, rotation_y, 0)
            except Exception:
                # Fallback: try setting rotation_y directly if entity supports it
                try:
                    ent.rotation_y = rotation_y
                except:
                    pass
            
            # Calculate label position based on entity height
            if hasattr(ent, 'scale') and len(ent.scale) >= 2:
                entity_height = ent.scale[1]
            else:
                entity_height = 2.4 * 1.2  # Default height
            
            # Position label above the player model - check if label is still valid
            if label and hasattr(label, 'nodePath') and label.nodePath and not label.nodePath.isEmpty():
                try:
                    label.position = Vec3(pdata["x"], pdata["y"] + entity_height / 2 + 0.5, pdata["z"])
                    label.text = pdata.get("name", "")
                except (AssertionError, AttributeError):
                    pass
            
            # Sync remote player health from server
            current_health = pdata.get("health", 100)
            max_health = pdata.get("max_health", 100)
            ent.health = current_health
            ent.max_health = max_health
            
            # Show/hide entity based on server health (dead players disappear until respawn)
            is_dead = current_health <= 0
            ent.enabled = not is_dead
            other_players[pid]["label"].enabled = not is_dead
    server_ids = {str(k) for k in server_players.keys()}
    for pid in list(other_players.keys()):
        if str(pid) not in server_ids:
            try:
                if other_players[pid].get("entity"):
                    destroy(other_players[pid]["entity"])
                if other_players[pid].get("label"):
                    other_players[pid]["label"].enabled = False
            except:
                pass
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
    
    # Get rotation from camera (yaw angle for horizontal rotation)
    rotation_y = camera.rotation_y if hasattr(camera, 'rotation_y') else 0
    
    pos = {
        "type": "position",
        "x": player.x,
        "y": player.y,
        "z": player.z,
        "rotation_y": rotation_y
    }
    try:
        sock.sendall(json.dumps(pos).encode() + b"\n")
    except:
        pass


def update():
    if not game_started or player is None:
        return
    if not pause_menu.paused:
        # Ensure mouse is locked for FirstPersonController to work
        if not mouse.locked:
            mouse.locked = True
            mouse.visible = False
        send_position()
        player_mod.update_local_player(player)
        
        # Sync local player health from server (server is authoritative)
        if my_id and my_id in server_players:
            server_health = server_players[my_id].get("health", 100)
            if hasattr(player, "health") and abs(player.health - server_health) > 0.1:
                player.health = server_health
            if health_bar.player_health != server_health:
                health_bar.player_health = server_health
                health_bar.update_health_bar()
            
            # Death/respawn handling based on server health
            if server_health <= 0 and not respawn.get_is_dead():
                respawn.die()
            elif server_health > 0 and respawn.get_is_dead():
                respawn.respawn()

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
    # Update leaderboard visibility - only show when TAB is held
    leaderboard.update_visibility()
    # Only update content when leaderboard is visible (TAB held)
    if leaderboard.is_visible() and held_keys.get('tab'):
        leaderboard.update_leaderboard()


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
