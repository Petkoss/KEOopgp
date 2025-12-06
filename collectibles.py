from ursina import *
import json

# --- COLLECTIBLES GLOBALS ---
server_collectibles = []  # list of collectibles from server
collectibles = {}
collectible_entities = {}
pending_collections = set()

# --- COLLECTIBLES UPDATE ---
def update_collectibles():
    global collectibles, collectible_entities, pending_collections
    collectible_ids_on_server = {c["id"] for c in server_collectibles}
    for cid in list(collectibles.keys()):
        if cid not in collectible_ids_on_server:
            destroy(collectibles[cid])
            del collectibles[cid]
            collectible_entities.pop(collectibles.get(cid), None)
            pending_collections.discard(cid)
    pending_collections.intersection_update(collectible_ids_on_server)
    for cdata in server_collectibles:
        cid = cdata["id"]
        if cid not in collectibles:
            c = Entity(model='sphere', color=color.yellow, texture='white_cube', scale=0.5,
                       position=(cdata["x"], cdata["y"], cdata["z"]))
            collectibles[cid] = c
            collectible_entities[c] = cid
            pending_collections.discard(cid)
    for cdata in server_collectibles:
        cid = cdata["id"]
        if cid in collectibles:
            collectibles[cid].position = Vec3(cdata["x"], cdata["y"], cdata["z"])

# --- COLLECTIBLES COLLISION CHECK ---
def check_collectibles(player, sock):
    if player is None or sock is None: return
    for c in list(collectibles.values()):
        if not c.enabled: continue
        distance = (player.position - c.position).length()
        if distance < 1.5:
            cid = collectible_entities.get(c)
            if cid and cid not in pending_collections:
                try:
                    sock.sendall(json.dumps({"type": "collect", "collectible_id": cid}).encode())
                    pending_collections.add(cid)
                    c.enabled = False
                except: pass

