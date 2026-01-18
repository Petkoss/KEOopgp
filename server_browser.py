from ursina import *
import socket, threading, json, random

PORT = 9999
SCAN_TIMEOUT = 0.25

# ----------------------------
# PATCH TEXTFIELD TO FIX _active ATTRIBUTE ERROR
# ----------------------------
def patch_textfield_class():
    """
    Monkey-patch TextField class to ensure _active attribute always exists.
    This prevents AttributeError when Ursina tries to access _active before it's initialized.
    """
    try:
        from ursina.prefabs.text_field import TextField
        original_active_getter = TextField.active.fget if hasattr(TextField.active, 'fget') else None
        
        def safe_active_getter(self):
            """Safe getter for active property that initializes _active if needed."""
            if not hasattr(self, '__dict__') or '_active' not in self.__dict__:
                object.__setattr__(self, '_active', False)
            return self.__dict__.get('_active', False)
        
        def safe_active_setter(self, value):
            """Safe setter for active property."""
            object.__setattr__(self, '_active', bool(value))
        
        # Replace the property with our safe version
        TextField.active = property(safe_active_getter, safe_active_setter)
    except Exception as e:
        # Silently fail if patching doesn't work
        pass

# Apply patch when module loads
patch_textfield_class()

def fix_inputfield_textfield(input_field):
    """
    Fix TextField _active attribute issue that causes AttributeError.
    This is a workaround for Ursina InputField/TextField initialization bug.
    """
    def _fix():
        try:
            if hasattr(input_field, 'text_field') and input_field.text_field:
                tf = input_field.text_field
                # Always use object.__setattr__ to avoid triggering property getter/setter
                try:
                    object.__setattr__(tf, '_active', False)
                except (AttributeError, KeyError):
                    pass
        except (AttributeError, KeyError):
            pass
    
    # Apply fix immediately
    _fix()
    
    # Also apply with delays to catch any late initialization
    from ursina import invoke
    invoke(_fix, delay=0.01)
    invoke(_fix, delay=0.05)
    invoke(_fix, delay=0.1)

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
        
        # Fix: Initialize _active attribute on TextField to prevent AttributeError
        fix_inputfield_textfield(self.name_input)
        
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

    def update(self):
        """Update method to fix TextField _active attribute issue."""
        try:
            if hasattr(self, 'name_input') and self.name_input:
                fix_inputfield_textfield(self.name_input)
        except:
            pass

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
        # First, properly clean up InputField to prevent TextField crashes
        if hasattr(self, 'name_input') and self.name_input:
            try:
                # Disable InputField first
                self.name_input.enabled = False
                # Fix TextField _active attribute before destroying to prevent crashes
                if hasattr(self.name_input, 'text_field') and self.name_input.text_field:
                    tf = self.name_input.text_field
                    # Ensure _active attribute exists and is False (use safe method)
                    try:
                        # Always use object.__setattr__ to avoid triggering property getter/setter
                        object.__setattr__(tf, '_active', False)
                    except (AttributeError, KeyError):
                        pass
                    # Disable TextField
                    tf.enabled = False
                    # Try to remove from scene's update list if possible
                    try:
                        from ursina import scene
                        if hasattr(scene, 'entities') and tf in scene.entities:
                            scene.entities.remove(tf)
                    except:
                        pass
                # Try to remove InputField from scene's update list
                try:
                    from ursina import scene
                    if hasattr(scene, 'entities') and self.name_input in scene.entities:
                        scene.entities.remove(self.name_input)
                except:
                    pass
                # Destroy the InputField
                destroy(self.name_input)
                self.name_input = None  # Clear reference
            except Exception as e:
                print(f"Error cleaning up name_input: {e}")
                # Force clear reference even if destroy fails
                try:
                    self.name_input = None
                except:
                    pass
        
        # Destroy buttons first
        for ent in list(self.buttons):
            try: 
                ent.enabled = False
                destroy(ent)
            except: pass
        self.buttons.clear()
        
        # Destroy all other UI elements
        for ent in list(self._ui_elems):
            try:
                ent.enabled = False
                    # If it's an InputField, clean up its TextField
                if hasattr(ent, '__class__') and 'InputField' in str(type(ent)):
                    if hasattr(ent, 'text_field') and ent.text_field:
                        tf = ent.text_field
                            # Ensure _active attribute exists and is False (use safe method)
                        try:
                                # Always use object.__setattr__ to avoid triggering property getter/setter
                            object.__setattr__(tf, '_active', False)
                        except (AttributeError, KeyError):
                            pass
                        tf.enabled = False
                        # Try to remove from scene's update list
                    try:
                        from ursina import scene
                        if hasattr(scene, 'entities') and tf in scene.entities:
                            scene.entities.remove(tf)
                    except:
                        pass
                    # Try to remove InputField from scene's update list
                    try:
                        from ursina import scene
                        if hasattr(scene, 'entities') and ent in scene.entities:
                            scene.entities.remove(ent)
                    except:
                        pass
                destroy(ent)
            except: pass
        self._ui_elems.clear()
        
        # Also destroy all children of the browser entity
        if hasattr(self, 'children'):
            for child in list(self.children):
                try:
                    child.enabled = False
                    destroy(child)
                except: pass

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
