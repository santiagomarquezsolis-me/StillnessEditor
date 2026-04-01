import os
import json
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from .constants import BASE_DIR, VERSION

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        """Loads or initializes the config.json file."""
        defaults = {
            "version": VERSION,
            "asset_paths": {
                "tiles": "assets/tiles",
                "rocks": "assets/sprites/zone_01_crash_site/misc",
                "structures": "assets/sprites/zone_01_crash_site/structure",
                "vfx": "assets/sprites/zone_01_crash_site/vfx",
                "sprites": "assets/sprites"
            }
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    # Sync version if missing or old
                    if data.get("version") != VERSION:
                        data["version"] = VERSION
                        self.save_config(data)
                    return data
            except: return defaults
        else:
            self.save_config(defaults)
            return defaults

    def save_config(self, config=None):
        """Saves current config to disk."""
        if config: self.config = config
        self.config["version"] = VERSION # Always ensure version is present
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
        except: pass

    def change_asset_paths(self):
        """Dialog with multiple entries for each resource path, stylized in Dark Mode with Icons."""
        root = tk.Tk()
        root.title("Stillness Editor - Resource Configuration")
        root.geometry("700x500")
        root.resizable(False, False)
        
        # Colors (Matching the Editor)
        BG_HEX = "#1E1E23"
        SURFACE_HEX = "#2D2D32"
        TEXT_HEX = "#DCDCDC"
        ACCENT_HEX = "#64C8FF"
        HIGHLIGHT_HEX = "#3A3A42"
        BORDER_HEX = "#4B4B52"

        root.configure(bg=BG_HEX)
        
        # Center the window
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"+{(sw-700)//2}+{(sh-500)//2}")

        # Load Icons using PIL
        icons = {}
        try:
            icon_path = os.path.join(BASE_DIR, "assets", "ui", "icons")
            folder_img = Image.open(os.path.join(icon_path, "folder_icon.png")).resize((18, 18), Image.Resampling.LANCZOS)
            save_img = Image.open(os.path.join(icon_path, "save_icon.png")).resize((20, 20), Image.Resampling.LANCZOS)
            icons['folder'] = ImageTk.PhotoImage(folder_img)
            icons['save'] = ImageTk.PhotoImage(save_img)
        except Exception as e:
            print(f"Error loading config icons: {e}")

        # Title Label
        tk.Label(root, text="RESOURCE CONFIGURATION", font=("Arial", 14, "bold"), 
                 bg=BG_HEX, fg=ACCENT_HEX).pack(pady=(20, 10))
        
        paths_to_edit = {
            "tiles": "TILES (Base Layer)",
            "rocks": "ROCKS (Objects Layer)",
            "structures": "STRUCTURES (Objects Layer)",
            "vfx": "VFX (Visual Effects Layer)"
        }
        
        entries = {}
        content_frame = tk.Frame(root, bg=BG_HEX)
        content_frame.pack(fill="both", expand=True, padx=40)

        for i, (key, label_text) in enumerate(paths_to_edit.items()):
            row = tk.Frame(content_frame, bg=BG_HEX)
            row.pack(fill="x", pady=8)
            
            # Label with Folder Icon
            header_row = tk.Frame(row, bg=BG_HEX)
            header_row.pack(side="top", fill="x", anchor="w")
            
            if 'folder' in icons:
                tk.Label(header_row, image=icons['folder'], bg=BG_HEX).pack(side="left", padx=(0, 5))
            
            lbl = tk.Label(header_row, text=label_text.upper(), font=("Arial", 9, "bold"), 
                           bg=BG_HEX, fg="#888899", anchor="w")
            lbl.pack(side="left")
            
            entry_row = tk.Frame(row, bg=BG_HEX)
            entry_row.pack(fill="x", pady=(2, 0))

            current_val = self.config.get("asset_paths", {}).get(key, "")
            entry = tk.Entry(entry_row, bg=SURFACE_HEX, fg=TEXT_HEX, insertbackground=ACCENT_HEX,
                             relief="flat", borderwidth=0, font=("Consolas", 10))
            entry.insert(0, current_val)
            entry.pack(side="left", fill="x", expand=True, ipady=5)
            entries[key] = entry
            
            def make_browse_func(e=entry):
                def browse():
                    path = filedialog.askdirectory(initialdir=BASE_DIR)
                    if path:
                        try:
                            rel = os.path.relpath(path, BASE_DIR)
                            if ".." not in rel: path = rel
                        except: pass
                        e.delete(0, tk.END)
                        e.insert(0, path)
                return browse
            
            btn_browse = tk.Button(entry_row, text="...", font=("Arial", 10, "bold"),
                                   bg=HIGHLIGHT_HEX, fg=TEXT_HEX, activebackground=ACCENT_HEX,
                                   activeforeground="black", relief="flat", borderwidth=0, 
                                   width=4, cursor="hand2", command=make_browse_func(entry))
            btn_browse.pack(side="right", padx=(5, 0))

        saved = [False]
        def save():
            for key, entry in entries.items():
                self.config["asset_paths"][key] = entry.get()
            self.save_config()
            saved[0] = True
            root.destroy()

        btn_row = tk.Frame(root, bg=BG_HEX)
        btn_row.pack(side="bottom", fill="x", padx=40, pady=25)
        
        # Save Button with Icon
        save_btn_params = {
            "text": " SAVE CONFIGURATION",
            "command": save,
            "bg": ACCENT_HEX,
            "fg": "black",
            "font": ("Arial", 11, "bold"),
            "relief": "flat",
            "cursor": "hand2",
            "activebackground": "#DCDCDC"
        }
        if 'save' in icons:
            save_btn_params["image"] = icons['save']
            save_btn_params["compound"] = "left"
            
        tk.Button(btn_row, **save_btn_params).pack(side="right", padx=(10, 0), ipadx=15, ipady=5)
                  
        tk.Button(btn_row, text="CANCEL", command=root.destroy, 
                  bg=BG_HEX, fg="#888899", font=("Arial", 10),
                  relief="flat", cursor="hand2", activeforeground=TEXT_HEX).pack(side="right", pady=5)

        root.mainloop()
        return saved[0]
