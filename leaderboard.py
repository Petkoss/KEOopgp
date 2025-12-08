from ursina import *

# --- LEADERBOARD GLOBALS ---
leaderboard_data = []  # List of (player_id, name, score) tuples, sorted by score
my_id = None
leaderboard_panel = None
leaderboard_title = None
leaderboard_entries = []  # List of Text entities for each entry

# --- LEADERBOARD SETUP ---
def setup_leaderboard(player_id):
    """Initialize leaderboard UI in top-right corner"""
    global my_id, leaderboard_panel, leaderboard_title, leaderboard_entries
    my_id = player_id
    
    # Background panel (semi-transparent, top-right corner)
    leaderboard_panel = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 150),  # Semi-transparent black
        scale=(0.25, 0.35),
        position=(0.85, 0.4, 0),  # Top-right corner
        origin=(0.5, 0.5)
    )
    
    # Title
    leaderboard_title = Text(
        text="LEADERBOARD",
        parent=camera.ui,
        position=(0.85, 0.55, -0.1),
        origin=(0.5, 0.5),
        scale=1.5,
        color=color.white,
        bold=True
    )
    
    # Initialize empty entries (will be updated)
    leaderboard_entries = []
    for i in range(10):  # Max 10 entries
        entry = Text(
            text="",
            parent=camera.ui,
            position=(0.85, 0.48 - i * 0.035, -0.1),
            origin=(0.5, 0.5),
            scale=1.0,
            color=color.white
        )
        leaderboard_entries.append(entry)
    
    update_leaderboard()

# --- LEADERBOARD UPDATE ---
def update_leaderboard_data(new_leaderboard):
    """Update leaderboard data from server"""
    global leaderboard_data
    leaderboard_data = new_leaderboard if new_leaderboard else []

def update_leaderboard():
    """Update leaderboard display"""
    global leaderboard_entries, leaderboard_data, my_id
    
    if not leaderboard_entries:
        return  # Not initialized yet
    
    if not leaderboard_data:
        # Clear all entries if no data
        for entry in leaderboard_entries:
            if entry:
                entry.text = ""
                entry.enabled = False
        return
    
    # Display top players (max 10)
    display_count = min(len(leaderboard_data), len(leaderboard_entries))
    
    for i in range(len(leaderboard_entries)):
        if i < display_count:
            player_id, name, score = leaderboard_data[i]
            
            # Highlight current player (convert to string for comparison)
            if str(player_id) == str(my_id):
                color_entry = color.yellow
                prefix = "> "
            else:
                color_entry = color.white
                prefix = f"{i+1}. "
            
            # Format: "1. PlayerName    50" or "> PlayerName    50"
            # Truncate name if too long
            max_name_len = 12
            display_name = name[:max_name_len] if len(name) <= max_name_len else name[:max_name_len-3] + "..."
            
            # Create formatted text with spacing
            entry_text = f"{prefix}{display_name:<15} {score:>4}"
            
            leaderboard_entries[i].text = entry_text
            leaderboard_entries[i].color = color_entry
            leaderboard_entries[i].enabled = True
        else:
            # Hide unused entries
            leaderboard_entries[i].text = ""
            leaderboard_entries[i].enabled = False

# --- LEADERBOARD TOGGLE (optional, for hiding/showing) ---
def set_visible(visible):
    """Show or hide leaderboard"""
    global leaderboard_panel, leaderboard_title, leaderboard_entries
    if leaderboard_panel:
        leaderboard_panel.enabled = visible
    if leaderboard_title:
        leaderboard_title.enabled = visible
    for entry in leaderboard_entries:
        if entry:
            entry.enabled = visible
