"""
Kill tracking module for server-side kill management.
Handles kill counting, leaderboard generation, and kill statistics.
"""

# Global kill tracking
kills = {}  # player_id -> kill count

def initialize_player(player_id):
    """Initialize kill count for a new player"""
    global kills
    kills[player_id] = 0

def award_kill(attacker_id, victim_id):
    """
    Award a kill to the attacker when victim dies.
    Returns True if kill was awarded, False otherwise.
    """
    global kills
    
    # Validate inputs
    if not attacker_id or not victim_id:
        return False
    
    if attacker_id == victim_id:
        # Can't kill yourself (suicide might be handled differently)
        return False
    
    # Award the kill
    if attacker_id not in kills:
        kills[attacker_id] = 0
    
    kills[attacker_id] += 1
    return True

def get_kills(player_id):
    """Get kill count for a player"""
    return kills.get(player_id, 0)

def get_all_kills():
    """Get dictionary of all player kills"""
    return kills.copy()

def reset_player_kills(player_id):
    """Reset kill count for a specific player"""
    if player_id in kills:
        kills[player_id] = 0

def reset_all_kills():
    """Reset all kill counts"""
    global kills
    for player_id in kills:
        kills[player_id] = 0

def remove_player(player_id):
    """Remove a player from kill tracking"""
    global kills
    if player_id in kills:
        del kills[player_id]

def get_leaderboard(players_dict):
    """
    Generate leaderboard sorted by kills.
    Returns list of tuples: (player_id, player_name, kills)
    """
    leaderboard = []
    
    for player_id, player_data in players_dict.items():
        name = player_data.get("name", f"Player{player_id}")
        kill_count = kills.get(player_id, 0)
        leaderboard.append((player_id, name, kill_count))
    
    # Sort by kills (descending), then by name
    leaderboard.sort(key=lambda x: (-x[2], x[1]))
    
    return leaderboard
