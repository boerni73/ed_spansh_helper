# Elite Dangerous - Spansh VR Navigator

A lightweight desktop helper for **Elite Dangerous** VR navigation.

This tool reads **Spansh route JSON files**, monitors your **Elite Dangerous journal logs**, copies the **next waypoint** to the clipboard, and generates a **navigation image** for use with **OpenKneeboard**.

---

## Features

- Load and parse **Spansh route JSON** files
- Supports multiple route types
- Monitors the latest **Elite Dangerous journal**
- Detects your current system after startup
- Tracks route progress
- Copies the **next waypoint** to the clipboard
- Generates a **VR navigation image**
- Displays the image inside the app
- Supports named **VR game versions**
- Lets you store **Ship Build JSON** snippets

---

## Required Downloads

The following tools/files must be installed or downloaded manually:

- **OpenXR DLL**
  https://znix.xyz/OpenComposite/download.php?arch=x64&branch=openxr

- **OpenKneeboard**
  https://openkneeboard.com/

- **VoiceAttack** or a similar clipboard/input automation tool
  https://voiceattack.com/
---

## What It Does

- Tries to determine the **next waypoint** of the loaded route
- Copies that waypoint to the **clipboard**
- Generates a **navigation image** that can be shown in VR with **OpenKneeboard**

This makes it easier to use Spansh routes while flying in VR.

---

## Typical Workflow

1. Start the app
2. Open **Settings**
3. Configure:
   - journal directory
   - kneeboard image output file
   - OpenXR DLL source
   - one or more stored game versions
4. Load a **Spansh route JSON**
5. Click **Start**
6. After each jump, the app updates the next waypoint and navigation image

---

## Installation

### Requirements

- Windows
- Python 3.10+ recommended
- Elite Dangerous
### Python packages

Install the required Python packages:

~~~bash
pip install -r requirements.txt
~~~

> `tkinter` is usually included with standard Python on Windows.

### Run

~~~bash
python ed_spansh_helper.py
~~~

### Build EXE

~~~bash
pyinstaller --noconsole --onefile ed_spansh_helper.py
~~~
---

## Notes

- The app does **not** paste waypoints into Elite Dangerous by itself
- It only copies the next waypoint to the **clipboard**
- To paste it into the galaxy map, use **VoiceAttack** or a similar tool
- The generated PNG can be displayed with **OpenKneeboard**
- VR DLL switching may require **administrator rights**
- After a game update, **VR setup may need to be run again**

---

## Recommended VR Setup

- **This app** for route tracking and image generation
- **OpenKneeboard** for displaying the image in VR
- **VoiceAttack** for inserting clipboard text into the galaxy map
- **OpenXR DLL / OpenComposite** for OpenXR mode

---

## Disclaimer

This is a helper utility for Elite Dangerous players.

Use it at your own risk and always verify your paths, DLL files, and automation setup.
