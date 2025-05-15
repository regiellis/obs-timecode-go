<h1 align="left">OBS Timecode Generator (Go Edition)</h1>

<p align="left">
  <strong>Bring frame-accurate, customizable timecode to your OBS Studio scenes with a fast Go backend and a simple Python client script.</strong>
</p>

<p align="left">
  <img src="https://img.shields.io/badge/Go-1.22+-00ADD8?logo=go&logoColor=white" alt="Go Version">
  <img src="https://img.shields.io/badge/OBS%20Studio-30.x-302E31?logo=obsstudio&logoColor=white" alt="OBS Studio Version">
  <img src="https://img.shields.io/badge/Python-3.6+-3776AB?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Cross--Platform-Yes-44CC11" alt="Cross Platform">
</p>

---

> [!NOTE]
> I built this tool to get better, frame-accurate timecode overlays for videos that will be used with Metahuman Animator and other workflow tools I plan to build for advanced video and animation pipelines in Unreal Engine.

---

## ✨ Why another OBS Timecode Generator?

*   🎥 **Frame-Accurate Timecode:** Get real-time, frame-precise timecode in your OBS scenes—perfect for live production, VOD, or creative overlays.
*   ⚡ **Go-Powered Speed:** The server is written in Go for reliability and low-latency updates.
*   🧩 **Separation of Concerns:** The Go server handles all time logic; the Python script just fetches and displays it.
*   🖥️ **Cross-Platform:** Works on Windows, macOS, and Linux (with minor tweaks if needed).
*   🛠️ **Customizable:** Supports 12/24hr, frames, date, UTC, prefix/suffix, and more.
*   🐍 **Easy OBS Integration:** The Python script provides a familiar UI in OBS and updates your text source automatically.

## 🚀 Quick Start

### 1. Download the Binaries

*   Get the latest `obs-timecode-server.exe` (Go server) and `obs-timecode-generator.py` (OBS Python script) from the [Releases page](https://github.com/yourusername/obs-timecode-generator/releases).

### 2. Run the Go Server

*   Double-click or run in terminal:
    ```powershell
    .\obs-timecode-server.exe [--port 8080] [--fps 30] [--debug]
    ```
*   By default, it listens on `127.0.0.1:8080` with 30 FPS.

### 3. Set Up OBS

*   Add a new **Text (GDI+)** source named **TimecodeDisplay** to your scene.
*   In OBS, go to **Tools > Scripts**, add `obs-timecode-generator.py`, and configure settings (host, port, format, etc.).
*   The script will connect to the Go server and update your text source in real time.

---

## 🛠️ Features

*   HH:MM:SS and HH:MM:SS:FF (frames) formats
*   12/24hr, AM/PM, date, UTC/GMT
*   Custom prefix/suffix
*   Error/status messages in the text source
*   All settings configurable in OBS


## 🧑‍💻 Building from Source

Want to build the Go server yourself? No problem!

1.  **Install Go:** ([https://go.dev/dl/](https://go.dev/dl/))
2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/yourusername/obs-timecode-generator.git
    cd obs-timecode-generator
    ```
3.  **Build the Server:**
    ```bash
    go mod tidy
    go build -o obs-timecode-server.exe .
    ```
    This will create `obs-timecode-server.exe` in the project directory.
4.  **(Optional) Edit or Extend:**
    *   The Go server code is in `main.go` and the `server/` directory.
    *   The OBS Python script is `obs-timecode-generator.py`—edit as needed for your workflow.

## 🖥️ Platform Notes

*   Developed and tested on Windows 10/11 with OBS Studio 30.x
*   Should work on macOS/Linux (feedback welcome!)
*   Both the Go server and Python script are designed to be cross-platform, but minor tweaks may be needed for non-Windows setups.

## 🐞 Troubleshooting

*   **"SERVER OFFLINE?" in OBS:** Make sure the Go server is running and the host/port match.
*   **No timecode, no error:** Check your text source name and OBS script log for Python errors.
*   **Go server crashes:** See the terminal for error messages.

## 🤝 Contributing

Pull requests, issues, and feedback are welcome—especially for cross-platform improvements and advanced workflow integrations!

---

<p align="center">
  Made with ❤️, and golang <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/go/go-original.svg" alt="Go" width="18" height="18"/>, and some Python <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="Python" width="18" height="18"/>
</p>