import os
import json
import tkinter as tk
from tkinter import filedialog
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
        """Dialog with multiple entries for each resource path, stylized in Dark Mode."""
        root = tk.Tk()
        root.title("Stillness Editor - Resource Configuration")
        root.geometry("650x450")
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
        root.geometry(f"+{(sw-650)//2}+{(sh-450)//2}")

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
        content_frame.pack(fill="both", expand=True, padx=30)

        for i, (key, label_text) in enumerate(paths_to_edit.items()):
            row = tk.Frame(content_frame, bg=BG_HEX)
            row.pack(fill="x", pady=8)
            
            lbl = tk.Label(row, text=label_text.upper(), font=("Arial", 9, "bold"), 
                           bg=BG_HEX, fg="#888899", width=22, anchor="w")
            lbl.pack(side="top", anchor="w")
            
            entry_row = tk.Frame(row, bg=BG_HEX)
            entry_row.pack(fill="x")

            current_val = self.config.get("asset_paths", {}).get(key, "")
            entry = tk.Entry(entry_row, bg=SURFACE_HEX, fg=TEXT_HEX, insertbackground=ACCENT_HEX,
                             relief="flat", borderwidth=0, font=("Consolas", 10))
            entry.insert(0, current_val)
            entry.pack(side="left", fill="x", expand=True, ipady=4)
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
        btn_row.pack(side="bottom", fill="x", padx=30, pady=25)
        
        tk.Button(btn_row, text="SAVE CONFIGURATION", command=save, width=20, 
                  bg=ACCENT_HEX, fg="black", font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2", activebackground="#DCDCDC").pack(side="right", padx=(10, 0))
                  
        tk.Button(btn_row, text="CANCEL", command=root.destroy, width=10, 
                  bg=BG_HEX, fg="#888899", font=("Arial", 10),
                  relief="flat", cursor="hand2", activeforeground=TEXT_HEX).pack(side="right")

        root.mainloop()
        return saved[0]
