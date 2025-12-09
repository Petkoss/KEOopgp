from ursina import *
import socket, threading, json

PORT = 9999
SCAN_TIMEOUT = 0.25

# ----------------------------
# LAN SCAN
# ----------------------------
def ping_server(ip):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(SCAN_TIMEOUT)
        s.connect((ip, PORT))
        data = s.recv(4096)
        js = json.loads(data.decode())
        if "id" in js:
            return True
        return False
    except:
        return False
    finally:
        try: s.close()
        except: pass

def scan_lan():
    local_ip = socket.gethostbyname(socket.gethostname())
    subnet = ".".join(local_ip.split(".")[:3])
    found = []
    threads = []

    def worker(ip):
        if ping_server(ip):
            found.append(ip)

    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        t = threading.Thread(target=worker, args=(ip,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return found

# ----------------------------
# SERVER BROWSER UI
# ----------------------------
class ServerBrowser(Entity):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.buttons = []

        # ------------------------------
        # Semi-transparent background (made bigger)
        # ------------------------------
        self.bg = Panel(
        parent=self,
        scale=Vec3(12, 10 ,1),
        color=color.rgba(0,0,0,190)
        )

        # Big title at the top (parented to camera.ui to be on top)
        self.main_title = Text(
            parent=camera.ui,
            text="KOŠICE ONLINE SERVERY",
            scale=3,
            y=0.4,
            origin=(0, 0),
            x=0,
            color=color.white,
            z=-0.1
        )

        # Title (parented to camera.ui to be on top)
        self.title = Text(parent=camera.ui, text="Searching for LAN servers...", scale=2, y=0.3, origin=(0,0), x=0, z=-0.1)

        # Refresh button
        self.refresh_btn = Button(
            parent=camera.ui,
            text="Refresh",
            scale=(0.75, 0.15),
            y=-0.35,
            color=color.azure
        )
        self.refresh_btn.on_click = self.refresh

        threading.Thread(target=self._scan, daemon=True).start()

    # Scan LAN servers
    def _scan(self):
        servers = scan_lan()
        # Ensure UI updates occur on main thread to avoid Panda3D NodePath asserts
        from ursina import invoke
        invoke(lambda: self._display_servers(servers))

    # Display server buttons
    def _display_servers(self, servers):
        # Clear previous buttons
        for b in self.buttons:
            destroy(b)
        self.buttons.clear()

        if not servers:
            self.title.text = "Server nenájdený. Skúste znova."
            return
        else:
            self.title.text = "Kliknite server pre pripojenie:"

        # Vertical layout starting position
        y_start = 0.15
        y_step = -0.25  # slightly increased spacing for bigger buttons

        for i, ip in enumerate(servers):
            b = Button(
                parent=camera.ui,  # <- make sure buttons are on top of all background UI
                text=f"{ip}:{PORT}",
                    scale=(0.9, 0.15),
                y=y_start + y_step*i,
                color=color.azure,
                text_origin=(0,0)
            )
            b.on_click = (lambda ip=ip: self._choose(ip))
            self.buttons.append(b)

    # When a server is clicked
    # When a server is clicked
    def _choose(self, ip):
    # Destroy all server buttons
        for b in self.buttons:
            destroy(b)
        self.buttons.clear()

        # Destroy the refresh button
        if hasattr(self, 'refresh_btn'):
            destroy(self.refresh_btn)

    # Destroy the background and title
        if hasattr(self, 'bg'):
            destroy(self.bg)
        if hasattr(self, 'main_title'):
            destroy(self.main_title)
        if hasattr(self, 'title'):
            destroy(self.title)

    # Destroy this entity (optional, for cleanup)
        destroy(self)

    # Delay slightly to ensure UI is cleared before starting game
        from ursina import invoke
        invoke(lambda: self.callback(ip), delay=0.05)
        
    # Refresh server list
    def refresh(self):
        self.title.text = "Hľadám servery..."
        threading.Thread(target=self._scan, daemon=True).start()

# ----------------------------
# API FUNCTION
# ----------------------------
def open_server_browser(callback):
    """
    Opens a server browser UI and calls `callback(ip)` when a server is clicked.
    """
    browser = ServerBrowser(callback)
    return browser
