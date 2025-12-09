from ursina import *
import time
import random

class Enemy(Entity):
    def __init__(self, **kwargs):
        super().__init__(model='cube', color=color.red, collider='box', health=100, **kwargs)
        self.last_shot_time = 0
        self.shoot_interval = random.uniform(1.5, 3.0)  # Random shooting interval
        self.damage = 5
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            destroy(self)
    
    def shoot_at_player(self, player):
        """Hitscan shoot at player - instant damage if in line of sight"""
        if not player or not player.enabled:
            return
        
        current_time = time.time()
        if current_time - self.last_shot_time < self.shoot_interval:
            return
        
        self.last_shot_time = current_time
        
        # Calculate direction to player
        direction = (player.position - self.position).normalized()
        shoot_origin = self.position + Vec3(0, 1, 0)  # Shoot from enemy's head height
        
        # Hitscan raycast from enemy to player
        hit_info = raycast(shoot_origin, direction, distance=100, ignore=[self])
        
        # Check if we hit the player
        if hit_info.hit and hit_info.entity == player:
            import health_bar
            health_bar.take_damage(self.damage)

