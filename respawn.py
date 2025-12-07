from ursina import *
import time
import health_bar

# Respawn state
is_dead = False
respawn_timer = 0
respawn_delay = 3.0
player = None

def set_player(player_entity):
    """Set the player reference"""
    global player
    player = player_entity

def die():
    """Handle player death"""
    global is_dead, respawn_timer
    
    if is_dead:
        return
    
    is_dead = True
    respawn_timer = time.time() + respawn_delay
    
    if player:
        player.enabled = False
        player.position = Vec3(0, -100, 0)  # Move player out of view
    
    # Show death message
    if health_bar.health_text:
        health_bar.health_text.text = "DEAD - Respawning..."
        health_bar.health_text.color = color.red

def respawn():
    """Respawn player after death"""
    global player, is_dead, respawn_timer
    
    if not is_dead:
        return
    
    is_dead = False
    respawn_timer = 0
    
    # Reset health
    health_bar.player_health = health_bar.max_health
    health_bar.is_dead = False
    
    if player:
        player.enabled = True
        player.position = Vec3(0, 2, 0)  # Respawn at starting position
        player.rotation = Vec3(0, 0, 0)  # Reset rotation
    
    health_bar.update_health_bar()
    
    if health_bar.health_text:
        health_bar.health_text.color = color.white

def update():
    """Update respawn system (check for respawn timer)"""
    global respawn_timer, is_dead
    
    if is_dead and respawn_timer > 0:
        if time.time() >= respawn_timer:
            respawn()

def get_is_dead():
    """Get death state"""
    return is_dead

