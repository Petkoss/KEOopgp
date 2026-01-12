from ursina import *

# --- LEADERBOARD GLOBALS ---
# Fullscreen čierny panel + jednoduchá tabuľka mien a skóre.
leaderboard_root = None
leaderboard_panel = None
leaderboard_title = None
header_player = None
header_kills = None
player_entries = []  # zoznam dictov {"name": Text, "kills": Text}
_visible = False
my_id = None
server_players_data = {}

def safe_text_create(**kwargs):
    """
    Safely create Text object with retry logic to handle font initialization issues.
    """
    try:
        # Try to create Text immediately
        return Text(**kwargs)
    except (AssertionError, AttributeError) as e:
        if "get_num_pages" in str(e) or "font" in str(e).lower():
            # Font not ready - try creating without bold first (bold font needs more initialization)
            kwargs_no_bold = kwargs.copy()
            kwargs_no_bold.pop('bold', None)
            try:
                text_obj = Text(**kwargs_no_bold)
                # If bold was requested, we'll add it later, but for now just return the text
                return text_obj
            except:
                # Last resort - minimal Text
                minimal_kwargs = {
                    'text': kwargs.get('text', ''),
                    'parent': kwargs.get('parent', camera.ui),
                    'position': kwargs.get('position', (0, 0, 0)),
                    'color': kwargs.get('color', color.white)
                }
                return Text(**minimal_kwargs)
        else:
            # Re-raise other errors
            raise

# --- LEADERBOARD SETUP ---
def setup_leaderboard(player_id):
    """Initialize fullscreen leaderboard UI (black screen with white text)."""
    global my_id, leaderboard_root, leaderboard_panel, leaderboard_title, header_player, header_kills, player_entries
    my_id = player_id
    
    # Root container to toggle všetko naraz; parent=camera.ui -> UI overlay
    leaderboard_root = Entity(parent=camera.ui, enabled=False)
    
    # Fullscreen čierne pozadie – rovnaký prístup ako server browser Panel
    # Veľká škála (12,10,1) pokryje celé okno bez ohľadu na rozlíšenie.
    leaderboard_panel = Panel(
        parent=leaderboard_root,
        scale=Vec3(12, 10, 1),
        color=color.rgba(0, 0, 0, 255)
    )
    
    # Názov a hlavičky stĺpcov (vo vnútri čiernej obrazovky)
    leaderboard_title = safe_text_create(
        text="LEADERBOARD",
        parent=leaderboard_root,
        scale=3,
        y=0.4,
        origin=(0, 0),
        color=color.white
    )
    
    header_player = safe_text_create(
        text="PLAYER",
        parent=leaderboard_root,
        scale=2,
        y=0.25,
        x=-0.4,
        origin=(-0.5, 0),
        color=color.white
    )
    
    header_kills = safe_text_create(
        text="KILLS",
        parent=leaderboard_root,
        scale=2,
        y=0.25,
        x=0.4,
        origin=(0.5, 0),
        color=color.white
    )
    
    # Riadky pre hráčov – jednoduchý text v dvoch stĺpcoch
    player_entries = []
    start_y = 0.15
    row_spacing = 0.06
    max_rows = 16
    for i in range(max_rows):
        row_y = start_y - i * row_spacing
        name_text = safe_text_create(
            text="",
            parent=leaderboard_root,
            scale=1.5,
            y=row_y,
            x=-0.4,
            origin=(-0.5, 0),
            color=color.white
        )
        kills_text = safe_text_create(
            text="",
            parent=leaderboard_root,
            scale=1.5,
            y=row_y,
            x=0.4,
            origin=(0.5, 0),
            color=color.white
        )
        player_entries.append({"name": name_text, "kills": kills_text})
    
    # Start hidden
    set_visible(False)

# --- LEADERBOARD UPDATE ---
def update_leaderboard_data(players_data):
    """Update raw data from server (dict id -> {name, kills})."""
    global server_players_data
    if players_data:
        server_players_data = players_data
    else:
        server_players_data = {}

def update_leaderboard():
    """Render player names and scores into the fullscreen leaderboard."""
    global player_entries, server_players_data, my_id
    
    if not player_entries:
        return
    
    # Ak nemáme žiadne dáta, zobraz krátku hlášku v prvom riadku
    if not server_players_data:
        entry = player_entries[0]
        entry["name"].text = "Waiting for player data..."
        entry["kills"].text = ""
        # Vymaž zvyšok riadkov
        for e in player_entries[1:]:
            e["name"].text = ""
            e["kills"].text = ""
        return
    
    # Pomocná funkcia na bezpečný prepočet skóre
    def get_kills_score(player_data):
        try:
            kills_raw = player_data.get("kills") or player_data.get("score") or 0
            return int(kills_raw) if kills_raw is not None else 0
        except (ValueError, TypeError):
            return 0
    
    # Zoradíme hráčov podľa killov zostupne
    sorted_players = sorted(
        server_players_data.items(),
        key=lambda item: get_kills_score(item[1]),
        reverse=True,
    )
    
    max_rows = len(player_entries)
    for i, entry in enumerate(player_entries):
        if i < len(sorted_players) and i < max_rows:
            player_id, pdata = sorted_players[i]
            name = pdata.get("name", f"Player{player_id}")
            kills = get_kills_score(pdata)
            
            # zvýrazni lokálneho hráča
            is_me = str(player_id) == str(my_id)
            prefix = "> " if is_me else f"{i+1}. "
            entry["name"].text = prefix + str(name)
            entry["name"].color = color.rgb(255, 255, 150) if is_me else color.white
            entry["kills"].text = str(kills)
            entry["kills"].color = color.rgb(255, 255, 150) if is_me else color.white
        else:
            entry["name"].text = ""
            entry["kills"].text = ""

# --- LEADERBOARD TOGGLE ---
def set_visible(visible):
    """Show or hide leaderboard (pure black screen)"""
    global leaderboard_root, leaderboard_panel, _visible
    _visible = visible
    
    # Len zobrazíme/skryjeme root kontajner, ktorý obsahuje čiernu obrazovku
    if leaderboard_root:
        leaderboard_root.enabled = visible
    
    # Skryjeme/zobrazíme health bar, aby nepresvietal cez leaderboard
    try:
        import health_bar
        health_bar.set_health_bar_visible(not visible)  # Skryj health bar keď je leaderboard viditeľný
    except:
        pass  # Ak health_bar nie je importovaný, ignoruj

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
