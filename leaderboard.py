from ursina import *

# --- LEADERBOARD GLOBALS ---
leaderboard_panel = None
leaderboard_title = None
header_player = None
header_kills = None
player_entries = []  # List of dicts with "bg" and "text" entities
_visible = False
my_id = None
server_players_data = {}

# --- LEADERBOARD SETUP ---
def setup_leaderboard(player_id):
    """Initialize fullscreen leaderboard UI"""
    global my_id, leaderboard_panel, leaderboard_title, header_player, header_kills, player_entries
    my_id = player_id
    
    # Fullscreen background panel - 50% opacity black
    # Scale of 2.0 covers full screen in camera.ui
    leaderboard_panel = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 128),  # 50% opacity (128/255 ≈ 0.5)
        scale=(2.0, 2.0),  # Full screen coverage
        position=(0, 0, 0),  # Center
        origin=(0.5, 0.5),  # Center origin
        z=-0.05
    )
    
    # Title at top center (centered on screen) - bigger
    # Create title text safely with error handling
    try:
        leaderboard_title = Text(
            text="TABUĽKA HRÁČOV",
            parent=camera.ui,
            position=(0, 0.5, -0.1),
            origin=(0.5, 0.5),
            scale=2.5,  # Reasonable size for title
            color=color.white,
            bold=True
        )
    except Exception as e:
        print(f"Warning: Could not create leaderboard title: {e}")
        leaderboard_title = Entity(parent=camera.ui, enabled=False)
    
    # Column headers (centered on screen) - bigger
    headers_y = 0.35
    try:
        header_player = Text(
            text="HRÁČ",
            parent=camera.ui,
            position=(-0.6, headers_y, -0.1),
            origin=(0, 0.5),
            scale=2.0,  # Reasonable size for headers
            color=color.white,
            bold=True
        )
    except Exception as e:
        print(f"Warning: Could not create header_player: {e}")
        header_player = Entity(parent=camera.ui, enabled=False)
    
    try:
        header_kills = Text(
            text="SKÓRE",
            parent=camera.ui,
            position=(0.6, headers_y, -0.1),
            origin=(1, 0.5),
            scale=2.0,  # Reasonable size for headers
            color=color.white,
            bold=True
        )
    except Exception as e:
        print(f"Warning: Could not create header_kills: {e}")
        header_kills = Entity(parent=camera.ui, enabled=False)
    
    # Initialize player entries (centered on screen) - bigger
    # Support up to 50 players to accommodate all players in a server
    player_entries = []
    start_y = 0.25
    spacing = 0.08  # Slightly reduced spacing to fit more players
    
    # Create entries - we'll create Text objects lazily when needed
    for i in range(50):  # Support up to 50 players
        y_pos = start_y - i * spacing
        
        # Row background - wider and taller
        entry_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(30, 30, 30, 120) if i % 2 == 0 else color.rgba(40, 40, 40, 120),
            scale=(2.2, 0.10),  # Wider and taller
            position=(0, y_pos, -0.08),
            origin=(0.5, 0.5),
            z=-0.06
        )
        
        # Store position for lazy Text creation
        # Text objects will be created on first use to avoid font initialization issues
        player_entries.append({
            "bg": entry_bg, 
            "name": None,  # Will be created lazily
            "kills": None,  # Will be created lazily
            "y_pos": y_pos  # Store position for lazy creation
        })
    
    # Start hidden
    set_visible(False)

# --- LEADERBOARD UPDATE ---
def update_leaderboard_data(players_data):
    """Update leaderboard data from server"""
    global server_players_data
    if players_data:
        server_players_data = players_data
    else:
        server_players_data = {}

def _ensure_text_objects(entry_index):
    """Lazily create Text objects for an entry if they don't exist"""
    global player_entries
    if entry_index >= len(player_entries):
        return
    
    entry = player_entries[entry_index]
    y_pos = entry.get("y_pos", 0.25 - entry_index * 0.08)
    
    # Create name text if it doesn't exist
    if entry["name"] is None:
        try:
            entry["name"] = Text(
                text="",
                parent=camera.ui,
                position=(-0.6, y_pos, -0.15),
                origin=(0, 0.5),
                scale=1.5,
                color=color.white,
                enabled=False
            )
        except Exception as e:
            print(f"Warning: Could not create name text for entry {entry_index}: {e}")
            entry["name"] = Entity(parent=camera.ui, enabled=False)
    
    # Create kills text if it doesn't exist
    if entry["kills"] is None:
        try:
            entry["kills"] = Text(
                text="",
                parent=camera.ui,
                position=(0.6, y_pos, -0.15),
                origin=(1, 0.5),
                scale=1.5,
                color=color.white,
                enabled=False
            )
        except Exception as e:
            print(f"Warning: Could not create kills text for entry {entry_index}: {e}")
            entry["kills"] = Entity(parent=camera.ui, enabled=False)

def update_leaderboard():
    """Update leaderboard display with current player data sorted by kills"""
    global player_entries, server_players_data, my_id
    
    if not player_entries:
        return  # Not initialized yet
    
    # If no data, show placeholder
    if not server_players_data:
        if len(player_entries) > 0:
            entry = player_entries[0]
            _ensure_text_objects(0)  # Ensure text objects exist
            if entry["name"] and hasattr(entry["name"], 'text'):
                try:
                    entry["name"].text = "Waiting for player data..."
                    entry["name"].color = color.white
                    entry["name"].enabled = True
                except:
                    if entry["name"]:
                        entry["name"].enabled = False
            if entry["kills"] and hasattr(entry["kills"], 'text'):
                try:
                    entry["kills"].text = ""
                    entry["kills"].enabled = False
                except:
                    pass
            if entry["bg"]:
                entry["bg"].enabled = True
            for i in range(1, len(player_entries)):
                if player_entries[i]["bg"]:
                    player_entries[i]["bg"].enabled = False
                if player_entries[i]["name"] and hasattr(player_entries[i]["name"], 'text'):
                    try:
                        player_entries[i]["name"].text = ""
                        player_entries[i]["name"].enabled = False
                    except:
                        pass
                if player_entries[i]["kills"] and hasattr(player_entries[i]["kills"], 'text'):
                    try:
                        player_entries[i]["kills"].text = ""
                        player_entries[i]["kills"].enabled = False
                    except:
                        pass
        return
    
    # Sort players by kills (score) in descending order
    def get_kills_score(player_data):
        """Safely extract kills/score as integer, defaulting to 0"""
        try:
            kills_raw = player_data.get("kills") or player_data.get("score") or 0
            return int(kills_raw) if kills_raw is not None else 0
        except (ValueError, TypeError):
            return 0
    
    sorted_players = sorted(
        server_players_data.items(),
        key=lambda x: get_kills_score(x[1]),  # Use kills, fallback to score, ensure int
        reverse=True
    )
    
    # Display ALL players (up to available entry slots)
    display_count = min(len(sorted_players), len(player_entries))
    
    for i in range(len(player_entries)):
        if i < display_count:
            # Ensure text objects exist before using them
            _ensure_text_objects(i)
            
            player_id, player_data = sorted_players[i]
            name = player_data.get("name", f"Player{player_id}")
            # Always get kills/score as integer using the same safe conversion
            kills = get_kills_score(player_data)
            
            # Highlight current player
            if str(player_id) == str(my_id):
                entry_color = color.rgba(50, 100, 200, 150)  # Blue highlight for current player
                text_color = color.rgb(255, 255, 100)  # Yellow text
                rank_prefix = f"> "
            else:
                entry_color = color.rgba(30, 30, 30, 100) if i % 2 == 0 else color.rgba(40, 40, 40, 100)
                text_color = color.white
                rank_prefix = f"{i+1}. "
            
            # Update background
            if player_entries[i]["bg"]:
                player_entries[i]["bg"].color = entry_color
                player_entries[i]["bg"].enabled = True
            
            # Format name: rank + name on left (no truncation needed if showing all)
            max_name_len = 25
            display_name = name[:max_name_len] if len(name) <= max_name_len else name[:max_name_len-3] + "..."
            
            # Update player name text (left side) - always show name
            if player_entries[i]["name"] and hasattr(player_entries[i]["name"], 'text'):
                text_entity = player_entries[i]["name"]
                full_text = f"{rank_prefix}{display_name}"
                # Ensure text is a proper string and update it
                try:
                    text_entity.text = str(full_text) if full_text else ""
                    text_entity.color = text_color
                    text_entity.enabled = True
                    # Ensure proper rendering
                    text_entity.origin = (0, 0.5)
                    text_entity.scale = 1.5  # Ensure scale is correct
                except Exception as e:
                    print(f"Warning: Could not update name text for entry {i}: {e}")
                    text_entity.enabled = False
            
            # Update kills text (right side) - ALWAYS show number, even if 0
            if player_entries[i]["kills"] and hasattr(player_entries[i]["kills"], 'text'):
                kills_entity = player_entries[i]["kills"]
                kills_text = str(kills)  # Always show as string number (including "0")
                try:
                    kills_entity.text = kills_text
                    kills_entity.color = text_color
                    kills_entity.enabled = True
                    # Ensure proper rendering
                    kills_entity.origin = (1, 0.5)
                    kills_entity.scale = 1.5  # Ensure scale is correct
                except Exception as e:
                    print(f"Warning: Could not update kills text for entry {i}: {e}")
                    kills_entity.enabled = False
        else:
            # Hide unused entries
            if player_entries[i]["bg"]:
                player_entries[i]["bg"].enabled = False
            if player_entries[i]["name"] and hasattr(player_entries[i]["name"], 'text'):
                try:
                    player_entries[i]["name"].text = ""
                    player_entries[i]["name"].enabled = False
                except:
                    pass
            if player_entries[i]["kills"] and hasattr(player_entries[i]["kills"], 'text'):
                try:
                    player_entries[i]["kills"].text = ""
                    player_entries[i]["kills"].enabled = False
                except:
                    pass

# --- LEADERBOARD TOGGLE ---
def set_visible(visible):
    """Show or hide leaderboard"""
    global leaderboard_panel, leaderboard_title, header_player, header_kills, player_entries, _visible
    _visible = visible
    
    if leaderboard_panel:
        leaderboard_panel.enabled = visible
    if leaderboard_title:
        leaderboard_title.enabled = visible
    if header_player:
        header_player.enabled = visible
    if header_kills:
        header_kills.enabled = visible
    
    # Show/hide entries based on visibility
    for entry in player_entries:
        if entry["bg"]:
            entry["bg"].enabled = visible
        if entry["name"]:
            entry["name"].enabled = visible
        if entry["kills"]:
            entry["kills"].enabled = visible

def is_visible():
    """Check if leaderboard is currently visible."""
    global _visible
    return _visible

def update_visibility():
    """Toggle visibility based on TAB being held."""
    global _visible
    # Check if TAB is currently held
    should_show = held_keys.get('tab', False) if hasattr(held_keys, 'get') else False
    # Only update if visibility state changed
    if should_show != _visible:
        set_visible(should_show)
