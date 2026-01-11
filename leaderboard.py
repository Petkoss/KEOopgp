from ursina import *

# -------------------------------------------------
# GLOBALS
# -------------------------------------------------
leaderboard_panel = None
leaderboard_title = None
header_player = None
header_kills = None

player_entries = []
_visible = False
my_id = None
server_players_data = {}

# -------------------------------------------------
# SETUP
# -------------------------------------------------
def setup_leaderboard(player_id):
    global my_id, leaderboard_panel, leaderboard_title, header_player, header_kills, player_entries
    my_id = player_id

    leaderboard_panel = Entity(
        parent=camera.ui,
        model='quad',
        scale=(2, 2),
        color=color.rgba(0, 0, 0, 180)
    )

    leaderboard_title = Text(
        "LEADERBOARD",
        parent=camera.ui,
        position=(0, 0.45),
        origin=(0.5, 0.5),
        scale=2,
        color=color.white,
        bold=True
    )

    header_player = Text(
        "PLAYER",
        parent=camera.ui,
        position=(-0.6, 0.33),
        origin=(0, 0.5),
        scale=1.3,
        color=color.white,
        bold=True
    )

    header_kills = Text(
        "KILLS",
        parent=camera.ui,
        position=(0.7, 0.33),
        origin=(1, 0.5),
        scale=1.3,
        color=color.white,
        bold=True
    )

    player_entries.clear()
    start_y = 0.25
    spacing = 0.075

    for i in range(20):
        y = start_y - i * spacing

        bg_color = color.rgb(40, 40, 40) if i % 2 == 0 else color.rgb(230, 230, 230)

        bg = Entity(
            parent=camera.ui,
            model='quad',
            scale=(1.9, 0.07),
            position=(0.05, y),
            color=bg_color
        )

        name = Text(
            "",
            parent=camera.ui,
            position=(-0.6, y),
            origin=(0, 0.5),
            scale=1.2
        )

        kills = Text(
            "",
            parent=camera.ui,
            position=(0.7, y),
            origin=(1, 0.5),
            scale=1.2
        )

        player_entries.append({
            "bg": bg,
            "name": name,
            "kills": kills,
            "index": i
        })

    set_visible(False)

# -------------------------------------------------
# DATA
# -------------------------------------------------
def update_leaderboard_data(players_data):
    global server_players_data
    server_players_data = players_data or {}

# -------------------------------------------------
# UPDATE
# -------------------------------------------------
def update_leaderboard():
    # -----------------------------
    # HARD-CODED VISIBILITY TEST
    # -----------------------------
    for entry in player_entries:
        entry["name"].text = ""
        entry["kills"].text = ""

    player_entries[0]["name"].text = "TEST PLAYER"
    player_entries[0]["kills"].text = "99"

    # -----------------------------
    # REAL DATA (IF PRESENT)
    # -----------------------------
    if not server_players_data:
        _apply_text_colors()
        return

    def score(p):
        return int(p.get("kills", p.get("score", 0)) or 0)

    sorted_players = sorted(
        server_players_data.items(),
        key=lambda x: score(x[1]),
        reverse=True
    )

    for i, (pid, pdata) in enumerate(sorted_players):
        if i >= len(player_entries):
            break

        entry = player_entries[i]
        name = pdata.get("name", f"Player{pid}")
        kills = score(pdata)
        is_me = str(pid) == str(my_id)

        entry["name"].text = f"{i+1}. {name}"
        entry["kills"].text = str(kills)

        if is_me:
            entry["bg"].color = color.rgb(60, 120, 200)

    _apply_text_colors()

# -------------------------------------------------
# TEXT COLOR CONTRAST
# -------------------------------------------------
def _apply_text_colors():
    for entry in player_entries:
        bg = entry["bg"].color
        dark = bg.r < 100

        text_color = color.white if dark else color.black

        entry["name"].color = text_color
        entry["kills"].color = text_color

# -------------------------------------------------
# VISIBILITY
# -------------------------------------------------
def set_visible(v):
    global _visible
    _visible = v

    leaderboard_panel.enabled = v
    leaderboard_title.enabled = v
    header_player.enabled = v
    header_kills.enabled = v

    for entry in player_entries:
        entry["bg"].enabled = v
        entry["name"].enabled = v
        entry["kills"].enabled = v

def is_visible():
    return _visible

def update_visibility():
    should_show = held_keys.get('tab', False)
    if should_show != _visible:
        set_visible(should_show)
