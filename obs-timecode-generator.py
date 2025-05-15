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
                f"PYTHON: HTTP GET Error from {url}, HTTP Status: {e.code}, Error: {e.reason}"
                + (f", Body: {error_body}" if did_read_error else "")
            )
        callback(False, error_body if did_read_error else None, e.code, str(e.reason))
    except urllib.error.URLError as e:
        if tcg_config["debug"]:
            print(f"PYTHON: HTTP GET URL Error to {url}, Reason: {e.reason}")
        callback(False, None, None, str(e.reason))
    except Exception as e:
        if tcg_config["debug"]:
            print(f"PYTHON: HTTP GET Unexpected Error to {url}, Error: {e}")
        callback(False, None, None, str(e))


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
        # Stop polling until source is visible again
        obs.timer_remove(tcg_poll_timecode)
        # Start a lightweight timer to check for source reappearance
        obs.timer_add(tcg_check_source_reappeared, 1000)
        return
    # ...existing polling logic (fetch timecode, update text)...


def tcg_check_source_reappeared():
    if tcg_is_source_visible():
        tcg_config["current_error_message"] = None
        obs.timer_remove(tcg_check_source_reappeared)
        obs.timer_add(tcg_poll_timecode, 1000)
        tcg_poll_timecode()

# In your script_load or timer setup, replace timer_add for polling with tcg_poll_timecode
# ...existing code...
