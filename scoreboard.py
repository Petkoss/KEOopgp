from ursina import *

# --- SCOREBOARD GLOBALS ---
scoreboard_panel = None
scoreboard_title = None
header_player = None
header_score = None
player_entries = []  # List of dicts with "bg" and "text" entities
_visible = False
my_id = None
server_players_data = {}

# --- SCOREBOARD SETUP ---
def setup_scoreboard(player_id):
    """Initialize fullscreen scoreboard UI"""
    global my_id, scoreboard_panel, scoreboard_title, header_player, header_score, player_entries
    my_id = player_id
    
    # Fullscreen background panel - covers entire screen
    # In Ursina camera.ui, scale 1.0 = screen size, so scale 3.0 ensures full coverage
    scoreboard_panel = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 240),  # Dark semi-transparent background
        scale=(3, 3),  # Extra large to ensure fullscreen coverage
        position=(0, 0, 0),  # Center
        origin=(0.5, 0.5),  # Center origin for proper centering
        z=-0.05
    )
    
    # Title at top center
    scoreboard_title = Text(
        text="TABUĽKA HRÁČOV",
        parent=camera.ui,
        position=(0, 0.85, -0.1),
        origin=(0.5, 0.5),
        scale=5.0,
        color=color.white,
        bold=True
    )
    
    # Column headers - positioned for fullscreen table
    headers_y = 0.65
    header_player = Text(
        text="HRÁČ",
        parent=camera.ui,
        position=(-0.6, headers_y, -0.1),
        origin=(0, 0.5),
        scale=3.0,
        color=color.white,
        bold=True
    )
    header_score = Text(
        text="SKÓRE",
        parent=camera.ui,
        position=(0.6, headers_y, -0.1),
        origin=(1, 0.5),
        scale=3.0,
        color=color.white,
        bold=True
    )
    
    # Initialize player entries
    player_entries = []
    start_y = 0.55  # Starting Y position
    spacing = 0.09  # Spacing between rows
    
    for i in range(16):  # Max 16 players
        y_pos = start_y - i * spacing
        
        # Row background - full width for fullscreen
        entry_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(40, 40, 40, 160) if i % 2 == 0 else color.rgba(50, 50, 50, 160),
            scale=(2.5, 0.1),  # Full width rows spanning most of screen
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
            scale=2.2,
            color=color.white
        )
        
        player_entries.append({"bg": entry_bg, "text": entry_text})
    
    # Start hidden
    set_visible(False)

# --- SCOREBOARD UPDATE ---
def update_scoreboard_data(players_data):
    """Update scoreboard data from server"""
    global server_players_data
    if players_data:
        server_players_data = players_data
    else:
        server_players_data = {}

def update_scoreboard():
    """Update scoreboard display with current player data"""
    global player_entries, server_players_data, my_id
    
    if not player_entries:
        return  # Not initialized yet
    
    # If no data, show placeholder
    if not server_players_data:
        # Show first entry with placeholder
        if len(player_entries) > 0:
            entry = player_entries[0]
            if entry["text"]:
                entry["text"].text = "Waiting for player data..."
                entry["text"].color = color.white
                entry["text"].enabled = True
            if entry["bg"]:
                entry["bg"].enabled = True
            # Hide other entries
            for i in range(1, len(player_entries)):
                if player_entries[i]["bg"]:
                    player_entries[i]["bg"].enabled = False
                if player_entries[i]["text"]:
                    player_entries[i]["text"].text = ""
                    player_entries[i]["text"].enabled = False
        return
    
    # Sort players by score (descending)
    sorted_players = sorted(
        server_players_data.items(),
        key=lambda x: x[1].get("score", 0),
        reverse=True
    )
    
    # Display players
    display_count = min(len(sorted_players), len(player_entries))
    
    for i in range(len(player_entries)):
        if i < display_count:
            player_id, player_data = sorted_players[i]
            name = player_data.get("name", f"Player{player_id}")
            score = player_data.get("score", 0)
            
            # Highlight current player
            if str(player_id) == str(my_id):
                entry_color = color.rgba(100, 150, 255, 200)  # Bright blue for current player
                text_color = color.rgb(255, 255, 100)  # Yellow text
            else:
                # Alternating colors for other players
                entry_color = color.rgba(40, 40, 40, 160) if i % 2 == 0 else color.rgba(50, 50, 50, 160)
                text_color = color.white
            
            # Update background
            if player_entries[i]["bg"]:
                player_entries[i]["bg"].color = entry_color
                player_entries[i]["bg"].enabled = True
            
            # Format text: name on left, score on right
            max_name_len = 30
            display_name = name[:max_name_len] if len(name) <= max_name_len else name[:max_name_len-3] + "..."
            
            if player_entries[i]["text"]:
                # Format with proper spacing for fullscreen display
                # Use wider spacing for better visibility
                player_entries[i]["text"].text = f"{display_name:<50} {score:>20}"
                player_entries[i]["text"].color = text_color
                player_entries[i]["text"].enabled = True
        else:
            # Hide unused entries
            if player_entries[i]["bg"]:
                player_entries[i]["bg"].enabled = False
            if player_entries[i]["text"]:
                player_entries[i]["text"].text = ""
                player_entries[i]["text"].enabled = False

# --- SCOREBOARD TOGGLE ---
def set_visible(visible):
    """Show or hide scoreboard"""
    global scoreboard_panel, scoreboard_title, header_player, header_score, player_entries, _visible
    _visible = visible
    
    if scoreboard_panel:
        scoreboard_panel.enabled = visible
    if scoreboard_title:
        scoreboard_title.enabled = visible
    if header_player:
        header_player.enabled = visible
    if header_score:
        header_score.enabled = visible
    
    # Show/hide entries based on visibility
    for entry in player_entries:
        if entry["bg"]:
            entry["bg"].enabled = visible
        if entry["text"]:
            entry["text"].enabled = visible

def update_visibility():
    """Toggle visibility based on TAB being held."""
    global _visible
    should_show = bool(held_keys.get('tab')) if hasattr(held_keys, "get") else held_keys.get('tab', False)
    if should_show != _visible:
        set_visible(should_show)
