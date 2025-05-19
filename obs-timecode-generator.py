# -*- coding: utf-8 -*-
"""
obs-timecode-generator.py
This script is an OBS (Open Broadcaster Software) plugin written in Python that provides functionality 
to display a timecode or custom text in a text source within OBS. It communicates with an external server 
to fetch or update configuration and text data, and updates the specified OBS text source accordingly.

Author:
- Regi Ellis
    - Email: regi@bynine.io
    - Email: regi@playlogic.io

Features:
- Configurable server host and port for HTTP communication.
- Supports both HTTP GET and POST requests to interact with the server.
- Allows customization of the displayed text, including pre-text, post-text, and time format (24-hour or UTC).
- Optionally displays the current date or frame count.
- Provides debug logging for HTTP requests and OBS source updates.
- Automatically retries configuration synchronization with the server if it fails.
- Updates the OBS text source dynamically based on the server response or internal state.

Key Components:
- `tcg_config`: A dictionary holding the script's configuration and internal state.
- `tcg_get_server_url`: Constructs the server URL with an optional endpoint.
- `tcg_http_post_json`: Sends an HTTP POST request with JSON data to the server and handles the response.
- `tcg_http_get`: Sends an HTTP GET request to the server and handles the response.
- `tcg_update_text_source`: Updates the specified OBS text source with the provided text or an error message.

Dependencies:
- OBS Python API (`obspython` module) for interacting with OBS.
- Standard Python libraries: `json`, `urllib.request`, `urllib.error`, `urllib.parse`, and `time`.

Usage:
- Configure the `tcg_config` dictionary with the desired settings, such as server host, port, and source name.
- Ensure the specified text source exists in OBS with the name defined in `tcg_config["source_name"]`.
- Enable debug mode (`tcg_config["debug"] = True`) for detailed logging during development or troubleshooting.

Note:
- The script assumes the presence of a text source in OBS with the name specified in `tcg_config["source_name"]`.
- Proper error handling is implemented for HTTP requests, but ensure the server is reachable and configured correctly.

Acknowledgment:
- This script is based on the original Lua script by spessoni/bozlo and serves as an alternative for those who prefer 
  a Python implementation or require more accurate timecode functionality.
"""


import obspython as obs
import json
import urllib.request
import urllib.error
import urllib.parse
import time
import threading
import queue

# --- Script State / Configuration ---
TCG_HARDCODED_SOURCE_NAME: str = "TimecodeDisplay"

tcg_config: dict = {
    "server_host": "127.0.0.1",
    "server_port": 8080,
    "source_name": TCG_HARDCODED_SOURCE_NAME,
    "time_mode": "24 Hour",
    "show_frame": False,
    "fps": 30,
    "show_date": False,
    "show_utc": False,
    "pre_text": "",
    "post_text": "",
    "keep_updated": False,
    "debug": False,
    # Internal state
    "is_source_active_in_pgm": False,
    "config_retry_timer_function": None,
    "one_second_timer_function": None,
    "is_config_synced_with_server": False,
    "current_error_message": None,
    "last_displayed_text": "",
}

TCG_HTTP_TIMEOUT_SECONDS: float = 2.0
TCG_CONFIG_RETRY_INTERVAL_MS: int = 5000

# Thread-safe queue for HTTP results
http_result_queue = queue.Queue()

# Timer function to process HTTP results on the main thread
def tcg_process_http_queue():
    try:
        while True:
            cb, args = http_result_queue.get_nowait()
            cb(*args)
    except queue.Empty:
        pass


def tcg_get_server_url(endpoint: str = "") -> str:
    return f"http://{tcg_config['server_host']}:{tcg_config['server_port']}{endpoint}"


def tcg_http_post_json(url: str, data_dict: dict, callback: callable) -> None:
    json_data: bytes = json.dumps(data_dict).encode("utf-8")
    req: urllib.request.Request = urllib.request.Request(
        url, data=json_data, headers={"Content-Type": "application/json"}, method="POST"
    )
    if tcg_config["debug"]:
        print(f"PYTHON: HTTP POST to {url} with data: {data_dict}")
    try:
        with urllib.request.urlopen(req, timeout=TCG_HTTP_TIMEOUT_SECONDS) as response:
            response_body: str = response.read().decode("utf-8")
            if tcg_config["debug"]:
                print(
                    f"PYTHON: POST Success to {url}, Status: {response.status}, Body snippet: {response_body[:100]}"
                )
            callback(True, response_body, response.status, None)
    except urllib.error.HTTPError as e:
        error_body: str = ""
        did_read_error: bool = False
        try:
            error_body = e.read().decode("utf-8")
            did_read_error = True
        except Exception:
            pass
        if tcg_config["debug"]:
            print(
                f"PYTHON: HTTP POST Error to {url}, HTTP Status: {e.code}, Error: {e.reason}"
                + (f", Body: {error_body}" if did_read_error else "")
            )
        callback(False, error_body if did_read_error else None, e.code, str(e.reason))
    except urllib.error.URLError as e:
        if tcg_config["debug"]:
            print(f"PYTHON: HTTP POST URL Error to {url}, Reason: {e.reason}")
        callback(False, None, None, str(e.reason))
    except Exception as e:
        if tcg_config["debug"]:
            print(f"PYTHON: HTTP POST Unexpected Error to {url}, Error: {e}")
        callback(False, None, None, str(e))


def tcg_http_get(url: str, callback: callable) -> None:
    def do_request():
        req: urllib.request.Request = urllib.request.Request(url, method="GET")
        if tcg_config["debug"]:
            print(f"PYTHON: HTTP GET from {url}")
        try:
            with urllib.request.urlopen(req, timeout=TCG_HTTP_TIMEOUT_SECONDS) as response:
                response_body: str = response.read().decode("utf-8")
                if tcg_config["debug"]:
                    print(
                        f"PYTHON: GET Success from {url}, Status: {response.status}, Body: {response_body}"
                    )
                http_result_queue.put((callback, (True, response_body, response.status, None)))
        except urllib.error.HTTPError as e:
            error_body: str = ""
            did_read_error: bool = False
            try:
                error_body = e.read().decode("utf-8")
                did_read_error = True
            except Exception:
                pass
            if tcg_config["debug"]:
                print(
                    f"PYTHON: HTTP GET Error from {url}, HTTP Status: {e.code}, Error: {e.reason}" + (f", Body: {error_body}" if did_read_error else "")
                )
            http_result_queue.put((callback, (False, error_body if did_read_error else None, e.code, str(e.reason))))
        except urllib.error.URLError as e:
            if tcg_config["debug"]:
                print(f"PYTHON: HTTP GET URL Error to {url}, Reason: {e.reason}")
            http_result_queue.put((callback, (False, None, None, str(e.reason))))
        except Exception as e:
            if tcg_config["debug"]:
                print(f"PYTHON: HTTP GET Unexpected Error to {url}, Error: {e}")
            http_result_queue.put((callback, (False, None, None, str(e))))
    threading.Thread(target=do_request, daemon=True).start()


def tcg_update_text_source(text_to_display: str) -> None:
    final_text: str = str(text_to_display)
    if tcg_config["current_error_message"]:
        final_text = tcg_config["current_error_message"]
    if final_text == tcg_config["last_displayed_text"]:
        return
    source = obs.obs_get_source_by_name(tcg_config["source_name"])
    if source:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", final_text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)
        tcg_config["last_displayed_text"] = final_text
    elif tcg_config["debug"]:
        print(
            f"PYTHON: ERROR - Text source '{tcg_config['source_name']}' not found. Please create it."
        )


def tcg_is_source_visible():
    source = obs.obs_get_source_by_name(tcg_config["source_name"])
    visible = False
    if source:
        scenes = obs.obs_frontend_get_scenes()
        for scene in scenes:
            scene_item = obs.obs_scene_find_source(obs.obs_scene_from_source(scene), tcg_config["source_name"])
            if scene_item and obs.obs_sceneitem_visible(scene_item):
                visible = True
            if scene_item:
                obs.obs_sceneitem_release(scene_item)
        obs.source_list_release(scenes)
        obs.obs_source_release(source)
    return visible


def tcg_poll_timecode():
    if not tcg_is_source_visible():
        tcg_config["current_error_message"] = "TIMECODE SOURCE MISSING OR HIDDEN?"
        tcg_update_text_source("")
        # Stop polling until user manually reconnects
        safe_timer_remove(tcg_poll_timecode)
        return
    # Poll the server for timecode if source is visible
    url = tcg_get_server_url("/timecode")
    tcg_http_get(url, handle_response)

    
def handle_response(success, body, status, error):
    if success:
        try:
            data = json.loads(body)
            display_text = data.get("display_text", "")
            tcg_config["current_error_message"] = None
            tcg_update_text_source(display_text)
        except Exception as e:
            tcg_config["current_error_message"] = f"SERVER RESPONSE ERROR: {e}"
            tcg_update_text_source("")
    else:
        tcg_config["current_error_message"] = f"SERVER ERROR: {error or status}"
        tcg_update_text_source("")


def script_description():
    return "Displays a timecode or custom text in a text source by polling an external server. Configure server and source below."


def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(props, "server_host", "Server Host", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "server_port", "Server Port", 1, 65535, 1)
    obs.obs_properties_add_text(props, "source_name", "Text Source Name", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_bool(props, "show_frame", "Show Frame Count")
    obs.obs_properties_add_int(props, "fps", "Frames Per Second", 1, 240, 1)
    obs.obs_properties_add_bool(props, "show_date", "Show Date")
    obs.obs_properties_add_bool(props, "show_utc", "Show UTC Time")
    obs.obs_properties_add_text(props, "pre_text", "Pre Text", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "post_text", "Post Text", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_bool(props, "keep_updated", "Keep Updated")
    obs.obs_properties_add_bool(props, "debug", "Debug Logging")
    obs.obs_properties_add_button(props, "reconnect_button", "Reconnect", on_reconnect_button_pressed)
    return props


def on_reconnect_button_pressed(props, prop):
    safe_timer_remove(tcg_poll_timecode)
    safe_timer_add(tcg_poll_timecode, 1000)
    tcg_poll_timecode()
    return True


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "server_host", "127.0.0.1")
    obs.obs_data_set_default_int(settings, "server_port", 8080)
    obs.obs_data_set_default_string(settings, "source_name", "TimecodeDisplay")
    obs.obs_data_set_default_bool(settings, "show_frame", False)
    obs.obs_data_set_default_int(settings, "fps", 30)
    obs.obs_data_set_default_bool(settings, "show_date", False)
    obs.obs_data_set_default_bool(settings, "show_utc", False)
    obs.obs_data_set_default_string(settings, "pre_text", "")
    obs.obs_data_set_default_string(settings, "post_text", "")
    obs.obs_data_set_default_bool(settings, "keep_updated", False)
    obs.obs_data_set_default_bool(settings, "debug", False)


def script_update(settings):
    tcg_config["server_host"] = obs.obs_data_get_string(settings, "server_host")
    tcg_config["server_port"] = obs.obs_data_get_int(settings, "server_port")
    tcg_config["source_name"] = obs.obs_data_get_string(settings, "source_name")
    tcg_config["show_frame"] = obs.obs_data_get_bool(settings, "show_frame")
    tcg_config["fps"] = obs.obs_data_get_int(settings, "fps")
    tcg_config["show_date"] = obs.obs_data_get_bool(settings, "show_date")
    tcg_config["show_utc"] = obs.obs_data_get_bool(settings, "show_utc")
    tcg_config["pre_text"] = obs.obs_data_get_string(settings, "pre_text")
    tcg_config["post_text"] = obs.obs_data_get_string(settings, "post_text")
    tcg_config["keep_updated"] = obs.obs_data_get_bool(settings, "keep_updated")
    tcg_config["debug"] = obs.obs_data_get_bool(settings, "debug")
    # Remove and re-add polling timer safely
    safe_timer_remove(tcg_poll_timecode)
    safe_timer_add(tcg_poll_timecode, 1000)
    # Ensure the HTTP result queue processor is running
    safe_timer_remove(tcg_process_http_queue)
    safe_timer_add(tcg_process_http_queue, 100)


def script_load(settings):
    # Remove and re-add polling timer safely
    safe_timer_remove(tcg_poll_timecode)
    safe_timer_add(tcg_poll_timecode, 1000)
    # Start the HTTP result queue processor
    safe_timer_remove(tcg_process_http_queue)
    safe_timer_add(tcg_process_http_queue, 100)

# --- Defensive Timer Management ---
timer_states = {
    'tcg_poll_timecode': False,
    'tcg_process_http_queue': False,
}

def safe_timer_add(callback, interval):
    name = callback.__name__
    if not timer_states.get(name, False):
        obs.timer_add(callback, interval)
        timer_states[name] = True
        if tcg_config.get('debug'):
            print(f"PYTHON: Timer added: {name}")

def safe_timer_remove(callback):
    name = callback.__name__
    if timer_states.get(name, False):
        obs.timer_remove(callback)
        timer_states[name] = False
        if tcg_config.get('debug'):
            print(f"PYTHON: Timer removed: {name}")
