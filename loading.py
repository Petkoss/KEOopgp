from ursina import *

# Úplne jednoduchý loading overlay – žiadne animácie ani extra entity.
loading_panel = None
loading_text = None


def show_loading_screen(message: str = "Načítavam..."):
    """Zobrazí jednoduchú čiernu overlay obrazovku s textom."""
    global loading_panel, loading_text

    hide_loading_screen()

    loading_panel = Entity(
        parent=camera.ui,
        model="quad",
        color=color.rgba(0, 0, 0, 220),
        scale=(2, 2),
        z=-0.1,
    )

    loading_text = Text(
        text=message,
        parent=loading_panel,
        origin=(0, 0),
        scale=2,
        color=color.white,
    )


def update_loading_screen(message: str | None = None):
    """Voliteľne zmení text; žiadna animácia, aby sme to mali jednoduché."""
    global loading_text
    if loading_text is not None and message is not None:
        loading_text.text = message


def hide_loading_screen():
    """Skryje a zničí overlay."""
    global loading_panel, loading_text

    if loading_panel is not None:
        destroy(loading_panel)
        loading_panel = None

    if loading_text is not None:
        destroy(loading_text)
        loading_text = None
