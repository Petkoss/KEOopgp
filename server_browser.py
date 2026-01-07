from ursina import *
import socket, threading, json, random

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

def scan_lan(extra_subnets=None):
    local_ip = socket.gethostbyname(socket.gethostname())
    primary_subnet = ".".join(local_ip.split(".")[:3])
    subnets = {primary_subnet}
    if extra_subnets:
        subnets.update(extra_subnets)
    found = []
    threads = []

    def worker(ip):
        if ping_server(ip):
            found.append(ip)

    for subnet in subnets:
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
        self._scanning = False
        self._ui_elems = []

        # ------------------------------
        # Semi-transparent background (made bigger)
        # ------------------------------
        self.bg = Panel(
        parent=self,
        scale=Vec3(12, 10 ,1),
        color=color.rgba(0,0,0,190)
        )
        self._ui_elems.append(self.bg)

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
        self._ui_elems.append(self.main_title)

        # Title (parented to camera.ui to be on top)
        self.title = Text(parent=camera.ui, text="Searching for LAN servers...", scale=2, y=0.3, origin=(0,0), x=0, z=-0.1)
        self._ui_elems.append(self.title)

        # Name input - simple text label and input field side by side
        self.name_label = Text(
            parent=camera.ui,
            text="Zadaj meno:",
            scale=1.3,
            y=-0.25,
            x=-0.15,
            origin=(0, 0),
            color=color.white,
            z=-0.1
        )
        # Name input field with white background for visibility
        self.name_input = InputField(
            parent=camera.ui,
            default_value="",
            scale=(0.4, 0.1),
            y=-0.25,
            x=0.25,
            origin=(0, 0),
            character_limit=20,
            color=color.white,  # White background
            z=-0.1
        )
        # Set hover color to keep it bright
        self.name_input.hover_color = color.rgb(255, 255, 255)
        
        # Set text color to black for visibility - try multiple times to ensure it works
        def set_text_color():
            try:
                if hasattr(self.name_input, 'text_entity') and self.name_input.text_entity:
                    self.name_input.text_entity.color = color.black
                elif hasattr(self.name_input, 'text_field'):
                    tf = self.name_input.text_field
                    if hasattr(tf, 'text_entity') and tf.text_entity:
                        tf.text_entity.color = color.black
            except:
                pass
        
        # Try immediately and after delay
        set_text_color()
        from ursina import invoke
        invoke(set_text_color, delay=0.1)
        invoke(set_text_color, delay=0.3)
        
        # Add a visible border around the input field
        try:
            border_scale = (self.name_input.scale_x * 1.05, self.name_input.scale_y * 1.05)
            border = Entity(
                parent=camera.ui,
                model='quad',
                scale=border_scale,
                position=(self.name_input.x, self.name_input.y, self.name_input.z - 0.01),
                color=color.rgb(100, 150, 255),  # Light blue border
                z=-0.11
            )
            self._ui_elems.append(border)
        except:
            pass
        self._ui_elems.append(self.name_label)
        self._ui_elems.append(self.name_input)

        # Refresh button - moved lower to accommodate name input
        self.refresh_btn = Button(
            parent=camera.ui,
            text="Refresh",
            scale=(0.75, 0.15),
            y=-0.42,
            color=color.azure
        )
        self.refresh_btn.on_click = self.refresh
        self._ui_elems.append(self.refresh_btn)

        threading.Thread(target=self._scan, daemon=True).start()

    # Scan LAN servers
    def _scan(self):
        if self._scanning:
            return
        self._scanning = True
        try:
            # Try primary subnet and a common Windows hotspot subnet (192.168.137.x)
            servers = scan_lan(extra_subnets={"192.168.137"})
            # Ensure UI updates occur on main thread to avoid Panda3D NodePath asserts
            from ursina import invoke
            invoke(lambda: self._safe_display(servers))
        finally:
            self._scanning = False

    def _safe_display(self, servers):
        try:
            self._display_servers(servers)
        except Exception as e:
            print(f"Server list render error: {e}")

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
            try:
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
                self._ui_elems.append(b)
            except Exception as e:
                print(f"Button create failed for {ip}: {e}")

    # When a server is clicked
    def _choose(self, ip):
        # get player name
        player_name = ""
        try:
            if hasattr(self, "name_input") and self.name_input:
                player_name = (self.name_input.text or "").strip()
        except:
            player_name = ""
        if not player_name:
            player_name = f"Player{random.randint(1000,9999)}"

        self._cleanup_ui()
        
        # Disable all UI elements before destroying
        for ent in self._ui_elems:
            try:
                ent.enabled = False
            except:
                pass
        
        # Destroy the browser entity
        try:
            destroy(self)
        except:
            pass

        # Delay slightly to ensure UI is cleared before starting game
        from ursina import invoke
        invoke(lambda: self.callback(ip, player_name), delay=0.05)
        
    # Refresh server list
    def refresh(self):
        self.title.text = "Hľadám servery..."
        threading.Thread(target=self._scan, daemon=True).start()

    def _cleanup_ui(self):
        # destroy all tracked ui entities
        for ent in self.buttons:
            try: destroy(ent)
            except: pass
        self.buttons.clear()
        for ent in self._ui_elems:
            try: destroy(ent)
            except: pass
        self._ui_elems.clear()

# ----------------------------
# API FUNCTION
# ----------------------------
_current_browser = None

def open_server_browser(callback):
    """
    Opens a server browser UI and calls `callback(ip)` when a server is clicked.
    """
    global _current_browser
    # Clean up any existing browser first
    if _current_browser:
        try:
            if hasattr(_current_browser, '_cleanup_ui'):
                _current_browser._cleanup_ui()
            destroy(_current_browser)
        except:
            pass
    _current_browser = ServerBrowser(callback)
    return _current_browser

def get_current_browser():
    """Get the current server browser instance"""
    return _current_browser
