from ursina import *

# Player health
player_health = 100
max_health = 100
player = None
is_dead = False

# UI elements
health_bar_bg = None
health_bar_fill = None
health_text = None

def get_health_color(health_percent):
    """Get color based on health percentage"""
    if health_percent > 0.6:
        return color.green
    elif health_percent > 0.3:
        return color.yellow
    else:
        return color.red

def setup_health_bar(player_entity):
    """Initialize health bar UI and set player reference"""
    global player, health_bar_bg, health_bar_fill, health_text, player_health, max_health, is_dead
    import respawn
    
    player = player_entity
    player_health = max_health
    is_dead = False
    
    # Set player reference in respawn module
    respawn.set_player(player_entity)
    
    # Health bar background (red/dark)
    health_bar_bg = Entity(
        parent=camera.ui,
        model='quad',
        color=color.dark_gray,
        scale=(0.3, 0.05),
        position=(-0.75, -0.45, 0),
        origin=(-0.5, -0.5)
    )
    
    # Health bar fill (green/red based on health)
    health_bar_fill = Entity(
        parent=camera.ui,
        model='quad',
        color=color.green,
        scale=(0.3, 0.05),
        position=(-0.75, -0.45, 0),
        origin=(-0.5, -0.5)
    )
    
    # Health text
    health_text = Text(
        text=f"{player_health}/{max_health}",
        origin=(0, 0),
        position=(-0.6, -0.385, -0.1),
        scale=2,
        color=color.white
    )
    
    update_health_bar()

def take_damage(amount):
    """Apply damage to player"""
    global player_health
    import respawn
    
    if respawn.get_is_dead():
        return
    
    player_health = max(0, player_health - amount)
    update_health_bar()
    
    if player_health <= 0:
        respawn.die()

def heal(amount):
    """Heal player"""
    global player_health, max_health
    import respawn
    
    if respawn.get_is_dead():
        return
    
    player_health = min(max_health, player_health + amount)
    update_health_bar()

def update_health_bar():
    """Update health bar visual"""
    global health_bar_fill, health_text, player_health, max_health
    
    if not health_bar_fill or not health_text:
        return
    
    # Calculate health percentage
    health_percent = player_health / max_health
    
    # Update fill width
    health_bar_fill.scale_x = 0.3 * health_percent
    
    # Update color (green -> yellow -> red)
    health_bar_fill.color = get_health_color(health_percent)
    
    # Update text
    health_text.text = f"{int(player_health)}/{max_health}"


