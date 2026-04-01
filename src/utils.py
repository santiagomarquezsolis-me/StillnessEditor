import tkinter as tk
from tkinter import filedialog
import os
from .constants import TILE_W, TILE_H, BASE_DIR

def world_to_screen(x, y, zoom, camera_offset):
    zw, zh = TILE_W * zoom, TILE_H * zoom
    sx = (x - y) * (zw // 2) + camera_offset.x
    sy = (x + y) * (zh // 2) + camera_offset.y
    return sx, sy

def screen_to_world(mx, my, zoom, camera_offset):
    mx -= camera_offset.x
    my -= camera_offset.y
    zw, zh = TILE_W * zoom, TILE_H * zoom
    x = (mx / (zw // 2) + my / (zh // 2)) / 2
    y = (my / (zh // 2) - mx / (zw // 2)) / 2
    return int(x), int(y)

def get_file_path(mode="save"):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    title = "SAVE MAP (JSON)" if mode == "save" else "LOAD MAP (JSON)"
    init_dir = os.path.join(BASE_DIR, "data", "maps")
    os.makedirs(init_dir, exist_ok=True)
    
    if mode == "save":
        path = filedialog.asksaveasfilename(title=title, initialdir=init_dir, defaultextension=".json", filetypes=[("JSON files", "*.json")])
    else:
        path = filedialog.askopenfilename(title=title, initialdir=init_dir, filetypes=[("JSON files", "*.json")])
    
    root.destroy()
    return path if path else None
