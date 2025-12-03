import platform
import threading
import traceback

if platform.system() == "Windows":
    import dxcam_cpp as dxcam
else:
    import dxcam

import keyboard
import pygetwindow as gw
import uvicorn

from core.assets import load_assets
from core.data.config import load_config
from core.execute import career_lobby
from core.global_state import GlobalState, load_global_data
from server.main import app
from update_config import update_config
from utils.log import debug, error, info
from utils.tools import sleep

TOGGLE_HOTKEY = "f1"

STEAM_WINDOW_NAME = "Umamusume"


def find_game_window(window_title: str) -> gw.BaseWindow | None:
    win = gw.getWindowsWithTitle(STEAM_WINDOW_NAME)
    target_window = next((w for w in win if w.title.strip() == STEAM_WINDOW_NAME), None)
    if not target_window:
        if not window_title:
            raise RuntimeError("Window name cannot be empty! Please set window name in the config.")
        info(f"Couldn't get the steam version window, trying {window_title}.")
        win = gw.getWindowsWithTitle(window_title)
        target_window = next((w for w in win if w.title.strip() == window_title), None)
        if not target_window:
            msg = f'Couldn\'t find target window named "{window_title}". Please double check your window name config.'
            raise RuntimeError(msg)
    return target_window


def focus_umamusume(window: gw.BaseWindow):
    try:
        if window.isMinimized:
            window.restore()
        else:
            window.minimize()
            sleep(0.2)
            window.restore()
            sleep(0.5)
    except Exception as e:
        error(f"Error focusing window: {e}")
        return False
    return True


def run_bot(state: GlobalState):
    print("Uma Auto!")
    try:

        if focus_umamusume(state.game_window):
            info(f"Config: {state.config.config_name}")
            career_lobby(state)
        else:
            error("Failed to focus Umamusume window")
    except Exception as e:
        error_message = traceback.format_exc()
        error(f"Error in main thread: {error_message}")
    finally:
        debug("[BOT] Stopped.")


def hotkey_listener(state: GlobalState):
    while True:
        keyboard.wait(TOGGLE_HOTKEY)
        with state.bot.bot_lock:
            if state.bot.is_bot_running:
                debug("[BOT] Stopping...")
                state.bot.stop_event.set()
                state.bot.is_bot_running = False

                if state.bot.bot_thread and state.bot.bot_thread.is_alive():
                    debug("[BOT] Waiting for bot to stop...")
                    state.bot.bot_thread.join(timeout=3)

                    if state.bot.bot_thread.is_alive():
                        debug("[BOT] Bot still running, please wait...")
                    else:
                        debug("[BOT] Bot stopped completely")

                state.bot.bot_thread = None
            else:
                debug("[BOT] Starting...")
                state.bot.is_bot_running = True
                state.bot.bot_thread = threading.Thread(target=run_bot, daemon=True, kwargs={"state": state})
                state.bot.bot_thread.start()
        sleep(0.5)


def start_server():
    host = "127.0.0.1"
    port = 8000
    info(f"Press '{TOGGLE_HOTKEY}' to start/stop the bot.")
    print(f"[SERVER] Open http://{host}:{port} to configure the bot.")
    config = uvicorn.Config(app, host=host, port=port, workers=1, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def main():
    info("Booting...")
    info("Updating config...")
    update_config()

    info("Loading config...")
    config = load_config()
    window = find_game_window("Umamusume")

    info("Loading assets and global data...")
    assets = load_assets("assets", window.height)
    state = GlobalState(
        assets=assets,
        data=load_global_data(window.height),
        game_window=window,
        config=config,
        cam=dxcam.create(),
    )
    info("Starting hotkey listener and server...")
    threading.Thread(target=hotkey_listener, daemon=True, kwargs={"state": state}).start()
    start_server()


if __name__ == "__main__":
    main()
