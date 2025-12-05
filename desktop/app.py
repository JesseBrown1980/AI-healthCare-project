"""Lightweight desktop wrapper for the Streamlit UI using PyWebview."""

import os
import pathlib

import webview

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
