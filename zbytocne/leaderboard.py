from ursina import *

# --- LEADERBOARD GLOBALS ---
leaderboard = []  # list of (player_id, name, score) tuples
leaderboard_bg = leaderboard_title = leaderboard_text = None

# --- LEADERBOARD SETUP ---
def setup_leaderboard():
    global leaderboard_bg, leaderboard_title, leaderboard_text
    leaderboard_bg = Entity(parent=camera.ui, model='quad',
                            color=color.rgba(64, 64, 64, 200),
                            scale=(0.35, 0.5), position=(-0.82, 0.4))
    leaderboard_title = Text("LEADERBOARD", parent=leaderboard_bg, y=0.45, scale=1.8,
                             origin=(0,0), color=color.black)
    leaderboard_text = Text("", parent=leaderboard_bg, y=0.25, scale=1.3, origin=(0,0),
                            color=color.black)

# --- LEADERBOARD UPDATE ---
def update_leaderboard(server_players=None, my_id=None):
    global leaderboard
    if leaderboard_text is None: return
    leaderboard_text.color = color.black
    if leaderboard_title: leaderboard_title.color = color.black
    lb_data = leaderboard if leaderboard else []
    if not lb_data and server_players:
        lb_data = [(pid, pdata.get("name","Player"), pdata.get("score",0))
                   for pid, pdata in server_players.items()]
        lb_data.sort(key=lambda x: x[2], reverse=True)
    display_text = "\n".join(
        f"{i+1}. {entry[1]}{' (you)' if str(entry[0])==str(my_id) else ''}: {entry[2]}"
        for i, entry in enumerate(lb_data[:10])
    ) if lb_data else "Waiting for players..."
    leaderboard_text.text = display_text
    leaderboard_text.color = color.black

