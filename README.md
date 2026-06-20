# Elite Dangerous - Spansh VR Navigator

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-personal-lightgrey)

A lightweight desktop helper for **Elite Dangerous** VR navigation.

This tool reads **Spansh route JSON files**, monitors your **Elite Dangerous journal logs**, copies the **next waypoint** to the clipboard, and generates a **navigation image** for use with **OpenKneeboard**.

---

## Table of Contents

- [Elite Dangerous - Spansh VR Navigator](#elite-dangerous---spansh-vr-navigator)
  - [Table of Contents](#table-of-contents)
  - [Motivation \& Background](#motivation--background)
    - [Development Note](#development-note)
  - [What It Does](#what-it-does)
  - [Required Downloads](#required-downloads)
  - [Installation](#installation)
    - [Requirements](#requirements)
    - [Python packages](#python-packages)
    - [Run](#run)
    - [Build EXE](#build-exe)
  - [Screenshots / Images](#screenshots--images)
    - [Main Window](#main-window)
    - [Generated Navigation Image](#generated-navigation-image)
  - [](#)
  - [Initial Setup](#initial-setup)
  - [Workflow to import a Spansh Route](#workflow-to-import-a-spansh-route)
  - [Example VoiceAttack Workflow](#example-voiceattack-workflow)
  - [Notes](#notes)
  - [Known Issues](#known-issues)
  - [Recommended VR Setup](#recommended-vr-setup)
  - [Disclaimer](#disclaimer)
  - [License](#license)

---

## Motivation & Background

I originally created this tool for myself to solve a specific pain point in Virtual Reality. While **spansh.co.uk** is an amazing website for route planning in Elite Dangerous, using it in VR was incredibly tedious. Copying and pasting each individual waypoint manually meant taking off and putting on my VR headset for every single jump. I wanted a smoother, seamless solution that keeps me immersed in the game.

### Development Note

This project was built with a lot of help from Large Language Models (LLMs). While the core ideas and custom logic are mine, LLMs assisted heavily in writing, refactoring, and restructuring almost the entire codebase to make it clean and functional.

## What It Does

The application is designed to make **VR route navigation** in Elite Dangerous more comfortable.

It continuously tries to determine the **next waypoint** of the loaded Spansh route based on your current location.

Whenever possible, it:

- identifies the next route target
- copies that system name to the **clipboard**
- generates a **navigation image**
- updates the image for viewing in **OpenKneeboard**

---

## Required Downloads

The following tools/files must be installed or downloaded manually:

- **OpenXR DLL**
  <https://znix.xyz/OpenComposite/download.php?arch=x64&branch=openxr>

- **OpenKneeboard**
  <https://openkneeboard.com/>

- **VoiceAttack** or a similar clipboard/input automation tool
  <https://voiceattack.com/>

---
## Installation

You can run the [provided .exe from the dist folder](dist/ed_spansh_helper.exe) or run the python script
>
> [!WARNING]
> **Antivirus False Positives:** Pre-compiled executables built with `pyinstaller` often trigger false malware warnings in Windows Defender or other antivirus software. This is a common issue with Python-to-EXE converters because they bundle the interpreter into a temporary directory. The tool contains absolutely no malicious code. If you prefer not to bypass your antivirus, you can always safely run the application from the source code using `python ed_spansh_helper.py`.

### Requirements

- Windows
- Python 3.10+ recommended

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

If you want to build your own Executable

~~~bash
pyinstaller --noconsole --onefile ed_spansh_helper.py
~~~

---

## Screenshots / Images

### Main Window

![Main Window](docs/images/main_window.png)

### Generated Navigation Image

![Generated Navigation Image](docs/images/navigation_image.png)
---

## Initial Setup

1. Start the app
2. Open **Settings**
3. journal directory. This is where ED writes the journal logs. default is C:\Users\YOUR_USER\Saved Games\Frontier Developments\Elite Dangerous
4. (optional) kneeboard image output file. This is the Path to the PNG-File that will be created and is used by OpenKneeboard
![Doc File-Tab Setup](docs/images/file_setup.png)
5. On the VR Mode Tab
Configure OpenXR DLL source. This is the Path to the OpenXR DLL you downloaded from [here](<https://znix.xyz/OpenComposite/download.php?arch=x64&branch=openxr>)
Let's assume you downloaded it to c:\tmp\newest_openxr.dll
![Doc VR-Mode-Tab Setup 1](docs/images/vr_mode_setup1.png)
6. Configure the Path to your ED OpenVR Folder. This is the folder that contains the ED's openvr_api.dll if you're not sure, search for it. I really don't know where this is located in your case... for me it's INSTALLATION_DIRECTORY\EDLaunch\Products\elite-dangerous-odyssey-64\Openvr\win64
![Doc VR-Mode-Tab Setup 2](docs/images/vr_mode_setup2.png)
7. If you selected the correct Path, you should see a setup required Message. Press "Setup/Re-Setup"
![Doc VR-Mode-Tab Setup 3](docs/images/vr_mode_setup3.png)
8. It should detect, that you're on the SteamVR/OpenVR Version. Press OpenXR
![Doc VR-Mode-Tab Setup 4](docs/images/vr_mode_setup4.png)

If everything worked, your EliteDangerous is now running with the OpenXR DLL, which is (probably) needed for OpenKneeboard, but even more important, should give you a significant FPS Boost.
You can change back anytime. If you're using some Steam-Overlay Software like OVR Toolkit, it's likely it won't work anymore. In the directory you specified, there are 3 Files now. openvr_api.dll (dll currently used), openvr_api.dll.steamvr (the original dll) and openvr_api.dll.openxr (a copy of the dll you downloaded). You can also manually rename these files to get back to your original configuration

## Workflow to import a Spansh Route

1. Load a **Spansh route JSON**
2. Click **Start**
3. Jump normally in Elite Dangerous
4. After each jump, the app updates:
   - current progress
   - next waypoint
   - navigation image

---

## Example VoiceAttack Workflow

This app copies the **next waypoint** to the clipboard, but it does **not** paste it into Elite Dangerous by itself.

A common setup is to use **VoiceAttack** to send the clipboard contents into the galaxy map search field.

Typical approach:

1. Open the galaxy map
2. Focus the search field
3. Trigger a VoiceAttack command
4. Let VoiceAttack send:
   - paste shortcut
   - confirm / search input
   - optional extra key presses for your personal workflow

This way, the waypoint copied by this tool can be inserted into the game with minimal manual work.

> The exact VoiceAttack profile depends on your own keybinds and preferred galaxy map workflow.

---

## Notes

- The app does **not** paste waypoints into Elite Dangerous by itself
- It only copies the next waypoint to the **clipboard**
- To paste it into the galaxy map, use **VoiceAttack** or a similar tool
- The generated PNG can be displayed with **OpenKneeboard**
- VR DLL switching may require **administrator rights**
- After a game update, **VR setup may need to be run again**

---

## Known Issues

- Very large journal files may slow down startup location detection
- VR DLL switching can fail if the game folder is protected
- After Elite Dangerous updates, the VR setup may need to be run again
- Clipboard-based workflows depend on external tools such as VoiceAttack
- Route matching may be less accurate if the current system is not directly part of the loaded route

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

Please note that this project is completely independent. Third-party tools and resources mentioned or integrated here—including **spansh.co.uk**, **OpenKneeboard**, **VoiceAttack** and the **OpenXR DLL**—are the property of their respective creators and are not affiliated with or developed by me.

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** License.

You are free to:

- **Share** — copy and redistribute the material in any medium or format.
- **Adapt** — remix, transform, and build upon the material.

Under the following terms:

- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
- **NonCommercial** — You may not use the material for commercial purposes.
- **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.

For more details, please see the full [Creative Commons Legal Code](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en).
