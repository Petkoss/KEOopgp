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
    
    # Title at top center (centered on screen)
    leaderboard_title = Text(
        text="LEADERBOARD",
        parent=camera.ui,
        position=(0, 0.4, -0.1),
        origin=(0.5, 0.5),
        scale=4.0,
        color=color.white,
        bold=True
    )
    
    # Column headers (centered on screen)
    headers_y = 0.25
    header_player = Text(
        text="PLAYER",
        parent=camera.ui,
        position=(-0.5, headers_y, -0.1),
        origin=(0, 0.5),
        scale=2.5,
        color=color.white,
        bold=True
    )
    header_kills = Text(
        text="KILLS",
        parent=camera.ui,
        position=(0.5, headers_y, -0.1),
        origin=(1, 0.5),
        scale=2.5,
        color=color.white,
        bold=True
    )
    
    # Initialize player entries (centered on screen)
    player_entries = []
    start_y = 0.15
    spacing = 0.08
    
    for i in range(20):  # Support up to 20 players
        y_pos = start_y - i * spacing
        
        # Row background
        entry_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(30, 30, 30, 100) if i % 2 == 0 else color.rgba(40, 40, 40, 100),
            scale=(1.8, 0.08),
            position=(0, y_pos, -0.08),
            origin=(0.5, 0.5),
            z=-0.06
        )
        
        # Player text
        entry_text = Text(
            text="",
            parent=camera.ui,
            position=(0, y_pos, -0.1),
            origin=(0.5, 0.5),
            scale=2.0,
            color=color.white
        )
        
        player_entries.append({"bg": entry_bg, "text": entry_text})
    
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

def update_leaderboard():
    """Update leaderboard display with current player data sorted by kills"""
    global player_entries, server_players_data, my_id
    
    if not player_entries:
        return  # Not initialized yet
    
    # If no data, show placeholder
    if not server_players_data:
        if len(player_entries) > 0:
            entry = player_entries[0]
            if entry["text"]:
                entry["text"].text = "Waiting for player data..."
                entry["text"].color = color.white
                entry["text"].enabled = True
            if entry["bg"]:
                entry["bg"].enabled = True
            for i in range(1, len(player_entries)):
                if player_entries[i]["bg"]:
                    player_entries[i]["bg"].enabled = False
                if player_entries[i]["text"]:
                    player_entries[i]["text"].text = ""
                    player_entries[i]["text"].enabled = False
        return
    
    # Sort players by kills (score) in descending order
    sorted_players = sorted(
        server_players_data.items(),
        key=lambda x: x[1].get("kills", x[1].get("score", 0)),  # Use kills, fallback to score
        reverse=True
    )
    
    # Display players
    display_count = min(len(sorted_players), len(player_entries))
    
    for i in range(len(player_entries)):
        if i < display_count:
            player_id, player_data = sorted_players[i]
            name = player_data.get("name", f"Player{player_id}")
            kills = player_data.get("kills", player_data.get("score", 0))
            
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
            
            # Format text: rank + name on left, kills on right
            max_name_len = 25
            display_name = name[:max_name_len] if len(name) <= max_name_len else name[:max_name_len-3] + "..."
            
            if player_entries[i]["text"]:
                # Format with proper spacing
                player_entries[i]["text"].text = f"{rank_prefix}{display_name:<30} {kills:>10}"
                player_entries[i]["text"].color = text_color
                player_entries[i]["text"].enabled = True
        else:
            # Hide unused entries
            if player_entries[i]["bg"]:
                player_entries[i]["bg"].enabled = False
            if player_entries[i]["text"]:
                player_entries[i]["text"].text = ""
                player_entries[i]["text"].enabled = False

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
        if entry["text"]:
            entry["text"].enabled = visible

def update_visibility():
    """Toggle visibility based on TAB being held."""
    global _visible
    should_show = bool(held_keys.get('tab', False)) if hasattr(held_keys, "get") else held_keys.get('tab', False)
    if should_show != _visible:
        set_visible(should_show)
