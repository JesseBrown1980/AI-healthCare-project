"""Lightweight desktop wrapper for the Streamlit UI using PyWebview.

Defaults to the Streamlit experience on port 3000 so the desktop shell
opens a working window against the same port used by docker-compose and
the Quick Start docs. Override `DESKTOP_APP_URL` if you want to point the
wrapper at a different frontend (for example, a React dev server).
"""

import os
import pathlib

import webview

# Default to the stack-wide Streamlit port (3000) while still allowing overrides
# for other frontends via DESKTOP_APP_URL (e.g., a React dev server on port
# 3000 or any custom deployment).
APP_URL = os.getenv("DESKTOP_APP_URL", "http://localhost:3000")
ICON_PATH = pathlib.Path(__file__).parent / "icon.png"


def main() -> None:
    window = webview.create_window(
        "Healthcare AI Assistant",
        url=APP_URL,
        width=1280,
        height=800,
        resizable=True,
        fullscreen=False,
        confirm_close=True,
        icon=str(ICON_PATH) if ICON_PATH.exists() else None,
    )
    webview.start(gui="edgechromium" if webview.available_gui("edgechromium") else None, debug=False)


if __name__ == "__main__":
    main()
