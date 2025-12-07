from ursina import *
import random

# --- CITY GENERATION ---
def generate_city(tile_size=5):
    spawn_position = Vec3(0, 2, 0)

    city_map = [
        "RRRRRRRRRRRRRRRRRRRR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RRRRRRRRRRRRRRRRRRRR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RRRRRRRRRRRRRRRRRRRR",
        "RSBBBBBPBBBBBBPBBBSR",
        "RRRRRRRRRRRRRRRRRRRR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RBBBBBBPBBBBBBPBBBBR",
        "RRRRRRRRRRRRRRRRRRRR",
    ]

    for z, row in enumerate(city_map):
        for x, cell in enumerate(row):
            world_x = x * tile_size - (len(row)*tile_size)/2
            world_z = z * tile_size - (len(city_map)*tile_size)/2

            if cell == "R":  # Road
                Entity(
                    model="cube", color=color.dark_gray,
                    scale=(tile_size, 0.1, tile_size),
                    position=(world_x, 0, world_z), collider="box"
                )

            elif cell == "B":  # Building
                # Safety: ensure building is not on road tile
                if cell == "B":
                    height = random.randint(12, 40)
                    Entity(
                        model="cube",
                        color=color.rgb(
                            random.randint(150, 255),
                            random.randint(150, 255),
                            random.randint(150, 255)
                        ),
                        scale=(tile_size*0.9, height, tile_size*0.9),
                        position=(world_x, height/2, world_z),
                        collider="box"
                    )

            elif cell == "P":  # Park
                Entity(
                    model="cube", color=color.lime.tint(-0.3),
                    scale=(tile_size, 0.2, tile_size),
                    position=(world_x, 0, world_z),
                    collider="box"
                )
                # Trees
                for i in range(random.randint(1,3)):
                    Entity(
                        model="cylinder", color=color.brown,
                        scale=(0.3,2,0.3),
                        position=(world_x + random.uniform(-1,1),
                                  1,
                                  world_z + random.uniform(-1,1))
                    )
                    Entity(
                        model="cone", color=color.green,
                        scale=(1,2,1),
                        position=(world_x + random.uniform(-1,1),
                                  2.5,
                                  world_z + random.uniform(-1,1))
                    )

            elif cell == "S":  # Player spawn
                spawn_position = Vec3(world_x, 2, world_z)

    return spawn_position

