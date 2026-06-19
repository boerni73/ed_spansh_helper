##########################################################################
# DATE              15.10.2022                                           #
#                                                                        #
# AUTHOR            Bernard Härri                                        #
#                                                                        #
# DESCRIPTION       Switches between openvr-DLL Versions for defined     #
#                   Games                                                #
#                                                                        #
# COMPILE: pyinstaller --noconsole --onefile openvr_switcher.py          #
#                                                                        #
##########################################################################
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import json
import os.path
import shutil
import sys
import hashlib
from pprint import pprint, pformat


def read_config(file):
    data = {}
    try:
        with open(file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        error(f"Could not load {file}: {e}")
    return data


def get_md5(path):
    try:
        file = open(path, 'rb')
    except Exception as e:
        error(f"Could not read File {path}: {e}")

    with file:
        data = file.read()
        md5 = hashlib.md5(data).hexdigest()

    return md5


def error(msg):
    messagebox.showerror("Error", msg)
    sys.exit(1)


def rb_select(game):
    dll2set = rb_vars[game].get()

    info.set(f"rb for {game} was selected. Value: {dll2set}")

    # Source and Destination
    src = cfg[game][dll2set]
    dest = cfg[game]['path2dll']

    # Copy File
    try:
        shutil.copyfile(src, dest)
    except Exception as e:
        error(f"Could not Copy {src} to {dest}: {e}")

    # Update Info
    info.set(f"{game} switched to {dll2set}")


# Main
# --- GUI --- #
root = tk.Tk()
root.title('OpenVR API DLL Switcher')
root['bg'] = 'black'
root.attributes('-toolwindow', True)

# ttk Style
s = ttk.Style()
s.configure('.', background='black', foreground='orange', font='TkDefaultFont 9')
s.configure('TLabelframe.Label', foreground='orange')
s.configure('TLabelframe', labeloutside=False)

# Infopane
info = tk.StringVar()
message = ttk.Label(
    root,
    textvariable=info,
    wraplength=220,
    anchor='center',
    relief='ridge'
)
message.pack(
    side=tk.BOTTOM,
    fill='x',
    anchor='s',
    expand=1,
    pady=5,
    ipady=3
)

info.set('OpenVR API DLL Switcher')

# Global vars
cfg = {}                                    # config Dict
lf = {}                                     # Dict to store the LabeledFrames
rb = {}                                     # Dict to store the RadioButoons
rb_vars = {}                                # Dict to store the Values of the RadioButtons

# Read Configuration
cfg = read_config('openvr_switcher.json')
openxr_src = 'openvr_api.dll.openxr'  # TODO: Update openxr.dll

# Loop throuh defined Games
for game in cfg:

    # Shortcut, g is a dict with the parameters for the current game
    g = cfg[game]
    md5_hashes = {}     # MD5-Hashes for the Current Game

    # Info
    info.set(f"Checking Files for Game {game}")

    # Check if openvr.dll is there
    if os.path.isfile(g['path2dll']):
        # If openvr.dll.steamvr is missing... (After Update)
        if not os.path.isfile(g['SteamVR']):
            if messagebox.askyesno(title="Has the Game been updated??",
                                   message=f"Do you want to copy {g['SteamVR']} from {g['path2dll']}?"):
                # Copy original Openvr.dll
                try:
                    shutil.copyfile(g['path2dll'], g['SteamVR'])
                except Exception as e:
                    error(f"Could not copy {g['path2dll']} to {g['SteamVR']}: {e}")

        # If openvr.dll.openxr is missing... (After Update)
        if not os.path.isfile(g['OpenXR']):
            if messagebox.askyesno(title="Has the Game been updated??",
                                   message=f"Do you want to copy {g['OpenXR']} from {openxr_src}?"):
                # Copy original openxr.dll from Default
                try:
                    shutil.copyfile(openxr_src, g['OpenXR'])
                except Exception as e:
                    error(f"Could not copy {openxr_src} to {g['OpenXR']}: {e}")

    # Check if all the defined Files are there
    for i in ['path2dll', 'SteamVR', 'OpenXR']:

        # If not, Error
        if not os.path.isfile(g[i]):
            error(f"Game {game}: {g[i]} is not a File!")

        # Build the md5-Hash for the defined 'SteamVR' and 'OpenXR' dll
        if i != 'path2dll':
            md5_hashes[get_md5(g[i])] = i

    # If we get here, all the Files exist
    info.set(f"Config for {game} seems to be ok.")

    # Currently Active DLL
    cur_md5 = get_md5(g['path2dll'])

    # If MD5 of current dll does not match either openvr nor openxr
    # maybe a newer version of the SteamVR dll
    if cur_md5 not in md5_hashes:
        error(f"md5-Hash of {g['path2dll']} ({cur_md5}) is unknown. Has the Game been updated?")

    # The Current Version of the DLL
    current = md5_hashes[cur_md5]

    # LabeledFrame per Game
    lf[game] = ttk.LabelFrame(
        root,
        text=game,
    )
    lf[game].pack(fill='x', expand=1, ipadx=5, pady=5)

    # Radiobuttons per Option
    rb_vars[game] = tk.StringVar()      # Every Game has its own StringVar
    rb_vars[game].set(current)          # Set the Var to the current DLL-Version

    for i in ['SteamVR', 'OpenXR']:
        rb[game] = ttk.Radiobutton(
            lf[game],
            text=i,
            value=i,
            variable=rb_vars[game],
            command=lambda t=game: rb_select(t)
        )
        rb[game].pack(side=tk.LEFT, ipadx=5, ipady=5)

root.mainloop()
