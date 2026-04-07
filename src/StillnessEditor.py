import pygame
import sys
import os
import json
from collections import deque
import copy
import copy
import random
from .constants import *
from .utils import world_to_screen, screen_to_world, get_file_path
from .config_manager import ConfigManager
from .asset_manager import AssetManager
from .ui_renderer import UIRenderer

class StillnessEditor:
    def __init__(self):
        pygame.init()
        # Set to desktop resolution by default (pseudo-maximized)
        display_info = pygame.display.Info()
        self.screen = pygame.display.set_mode((display_info.current_w, display_info.current_h - 60), pygame.RESIZABLE)
        self.w, self.h = self.screen.get_size()
        pygame.display.set_caption(f"Stillness Point - World Editor {VERSION}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.bold_font = pygame.font.SysFont("Arial", 18, bold=True)

        # Managers
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        self.cm = ConfigManager(config_path)
        self.am = AssetManager()
        self.ui = UIRenderer(self)

        # State
        self.running = True
        self.current_layer = LAYER_BASE
        self.current_cat = None
        self.selected_item = None
        self.search_query = "" # REQ-EFF-03
        self.brush_fh = self.brush_fv = self.brush_shadow = self.brush_scatter = False
        self.brush_rot = 0
        self.zoom_level = 1.0
        self.top_bar_height = 30
        self.camera_offset = pygame.Vector2(self.w // 2, self.h // 4 + self.top_bar_height)
        self.show_grid = True
        self.active_menu = None
        self.confirm_target = None
        self.modal_buttons = []
        self.ui_panel_width = 250
        self.status_message = None
        self.status_timer = 0
        self.search_active = False # REQ-EFF-03 (Focus)
        self.palette_scroll_y = 0
        self.max_palette_scroll = 0
        
        # Level 3: Selection & Clipboard (REQ-EFF-04)
        self.selection_start = None
        self.selection_end = None
        self.clipboard = None
        self.paste_mode = False
        self.paste_offset = (0, 0)
        self.metadata_focus = False # REQ-DATA-01
        
        # History (REQ-EFF-01)
        self.undo_stack = deque(maxlen=UNDO_LIMIT)
        self.redo_stack = deque(maxlen=UNDO_LIMIT)

        # Weather & Effects
        self.show_fog = False
        self.show_rain = False
        self.fog_presets = [
            (255, 255, 255), # White
            (100, 100, 110), # Gray
            (180, 210, 180), # Swamp Green
            (180, 180, 210), # Misty Blue
            (50, 50, 60)      # Deep Night
        ]
        self.fog_color_idx = 0
        self.rain_particles = [] # List of [x, y, speed, length]
        self.rain_collision_floor = True
        self.rain_collision_objects = True
        self.rain_splashes = True
        self.rain_density = 100
        self.rain_angle = 0 # Offset for screen X: -20 to 20 px per frame
        self.splashes = [] # List of {"x": x, "y": y, "life": life}
        self.show_weather_config = False
        self.init_rain()

        self.menu_items = {
            "FILE": [("New Map", "reset"), ("Open...", "load"), ("Save As...", "save"), ("Configuration", "config"), ("-", ""), ("Exit", "exit")],
            "EDIT": [("Undo [Ctrl+Z]", "undo"), ("Redo [Ctrl+Y]", "redo"), ("-", ""), ("Flip H [F]", "flip_h"), ("Flip V [V]", "flip_v"), ("Rotate [R]", "rotate"), ("Scatter [P]", "scatter"), ("Reset [X]", "clear")],
            "VIEW": [("Toggle Grid [H]", "grid"), ("Toggle Sidebar", "sidebar"), ("-", ""), ("Weather Settings...", "weather_config")],
            "LAYER": [("Base [1]", LAYER_BASE), ("Objects [2]", LAYER_OBJECTS), ("VFX [3]", LAYER_VFX), ("Collision [4]", LAYER_COLLISION), ("Animations [5]", LAYER_ANIM)]
        }

        self.grid = [[{
            "base_id": None, "base_fh": False, "base_fv": False, "base_rot": 0,
            "objects_id": None, "objects_fh": False, "objects_fv": False, "objects_rot": 0, "objects_shadow": False,
            "vfx_id": None, "vfx_fh": False, "vfx_fv": False, "vfx_rot": 0,
            "collision": False,
            "offset_x": 0, "offset_y": 0, "metadata": "" # REQ-DETAIL-01, REQ-DATA-01
        } for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

        self.am.load_assets(self.cm.config)
        self.update_ui_layout()
        self.refresh_palette()

    def save_snapshot(self):
        """Saves current grid state to undo stack."""
        self.undo_stack.append(copy.deepcopy(self.grid))
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.grid))
            self.grid = self.undo_stack.pop()
            self.status_message = "UNDO"
            self.status_timer = 60

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.grid))
            self.grid = self.redo_stack.pop()
            self.status_message = "REDO"
            self.status_timer = 60

    def init_rain(self):
        zw, zh = TILE_W * self.zoom_level, TILE_H * self.zoom_level
        self.rain_particles = []
        for _ in range(self.rain_density):
            gx, gy = random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1)
            # screen_x = (gx - gy) * (zw // 2) + self.camera_offset.x
            # target_y = (gx + gy + 1) * (zh // 2) + self.camera_offset.y
            self.rain_particles.append({
                "gx": gx, "gy": gy,
                "y": random.randint(-self.h, self.h),
                "speed": random.randint(10, 20),
                "len": random.randint(10, 20)
            })

    def spawn_splash(self, x, y):
        if self.rain_splashes:
            self.splashes.append({"x": x, "y": y, "life": 10})

    def draw_fog_effect(self):
        if not self.show_fog: return
        fog_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        color = self.fog_presets[self.fog_color_idx]
        fog_surf.fill((*color, 80)) 
        self.screen.blit(fog_surf, (0, 0))

    def draw_rain_effect(self):
        if not self.show_rain: return
        import random
        zw, zh = TILE_W * self.zoom_level, TILE_H * self.zoom_level
        
        # Update and Draw Splashes
        for s in self.splashes[:]:
            alpha = int((s["life"] / 10) * 200)
            pygame.draw.circle(self.screen, (200, 200, 220, alpha), (int(s["x"]), int(s["y"])), 2 + (10 - s["life"]))
            s["life"] -= 1
            if s["life"] <= 0: self.splashes.remove(s)

        # Update and Draw Rain
        for p in self.rain_particles:
            # Calculate current screen position based on gx, gy and camera
            # (Adding camera offset here so they move with the camera)
            sx = (p["gx"] - p["gy"]) * (zw // 2) + self.camera_offset.x
            target_y = (p["gx"] + p["gy"] + 1) * (zh // 2) + self.camera_offset.y
            
            # Adjust target_y for objects if enabled
            if self.rain_collision_objects:
                cell = self.grid[p["gx"]][p["gy"]]
                if cell.get(f"{LAYER_OBJECTS}_id"):
                    # Estimate object height (simple 40px * zoom default for now)
                    target_y -= 40 * self.zoom_level
                elif not self.rain_collision_floor:
                    target_y = self.h + 100 # Fall through floor
            elif not self.rain_collision_floor:
                target_y = self.h + 100

            # Draw
            off_x = (p["y"] / 10) * self.rain_angle # Simulating angle
            pygame.draw.line(self.screen, (170, 180, 200, 150), (sx + off_x, p["y"]), (sx + off_x - self.rain_angle//2, p["y"] + p["len"]), 1)
            
            # Move
            p["y"] += p["speed"]
            
            # Collision check
            if p["y"] >= target_y:
                self.spawn_splash(sx + off_x, target_y)
                p["y"] = -random.randint(50, self.h)
                p["gx"] = random.randint(0, GRID_SIZE-1)
                p["gy"] = random.randint(0, GRID_SIZE-1)

    def bucket_fill(self, start_x, start_y):
        if not self.selected_item: return
        key = "vfx" if self.current_layer == LAYER_ANIM else self.current_layer
        target_id = self.grid[start_x][start_y].get(f"{key}_id")
        if target_id == self.selected_item: return
        
        self.save_snapshot()
        queue = deque([(start_x, start_y)])
        visited = set([(start_x, start_y)])
        
        while queue:
            x, y = queue.popleft()
            self.grid[x][y][f"{key}_id"] = self.selected_item
            if self.current_layer == LAYER_OBJECTS: self.grid[x][y]["objects_shadow"] = self.brush_shadow
            
            for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    if (nx, ny) not in visited and self.grid[nx][ny].get(f"{key}_id") == target_id:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        self.status_message = f"BUCKET FILL ({self.current_layer.upper()}) APPLIED"
        self.status_timer = 120

    def copy_selection(self):
        if self.selection_start and self.selection_end:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            min_x, max_x = min(x1, x2), max(x1, x2)
            min_y, max_y = min(y1, y2), max(y1, y2)
            
            self.clipboard = []
            for x in range(min_x, max_x + 1):
                row = []
                for y in range(min_y, max_y + 1):
                    row.append(copy.deepcopy(self.grid[x][y]))
                self.clipboard.append(row)
            self.status_message = f"COPIED {len(self.clipboard)}x{len(self.clipboard[0])} AREA"
            self.status_timer = 90

    def cut_selection(self):
        if self.selection_start and self.selection_end:
            self.copy_selection()
            self.save_snapshot()
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    self.grid[x][y] = {k: (None if "id" in k else (0 if "offset" in k else ("" if k=="metadata" else False))) for k in self.grid[x][y].keys()}
            self.status_message = "AREA CUT"
            self.status_timer = 90

    def paste_at(self, start_x, start_y):
        if not self.clipboard: return
        self.save_snapshot()
        for i, row in enumerate(self.clipboard):
            for j, cell in enumerate(row):
                tx, ty = start_x + i, start_y + j
                if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                    self.grid[tx][ty] = copy.deepcopy(cell)
        self.status_message = "AREA PASTED"
        self.status_timer = 90
        self.paste_mode = False

    def refresh_palette(self):
        self.palette_buttons = []
        if self.current_layer not in self.am.assets: return
        x_start, y_start = self.w - self.ui_panel_width + 10, self.top_bar_height + 360
        thumb_w, thumb_h = (self.ui_panel_width - 36) // 2, 60
        
        # Filtering logic (REQ-EFF-03)
        if self.current_layer == LAYER_ANIM:
            assets = {k: v for k, v in self.am.assets[LAYER_ANIM].items() if self.search_query.lower() in k.lower()}
            for i, (name, img) in enumerate(assets.items()):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img, "anim": True})
            return

        assets = self.am.assets[self.current_layer]
        if self.current_layer == LAYER_BASE:
            items = {k: v for k, v in assets["main"].items() if self.search_query.lower() in k.lower()}
            for i, (name, img) in enumerate(items.items()):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img})
        elif not self.current_cat:
            for i, cat in enumerate(assets):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": cat, "type": "category"})
        else:
            raw_items = assets.get(self.current_cat, {})
            items = {k: v for k, v in raw_items.items() if self.search_query.lower() in k.lower()}
            display_items = [(".. BACK", None)] + list(items.items())
            for i, (name, img) in enumerate(display_items):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w+10), y_start + (i//2)*(thumb_h+10), thumb_w, thumb_h)
                if name == ".. BACK": self.palette_buttons.append({"rect": rect, "name": name, "type": "back"})
                else: self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img})
        
        # Calculate Max Scroll
        visible_h = self.h - (y_start + 10)
        total_h = ((len(self.palette_buttons) + 1) // 2) * (thumb_h + 10)
        self.max_palette_scroll = max(0, total_h - visible_h + 20)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.VIDEORESIZE: self.w, self.h = event.w, event.h; self.update_ui_layout(); self.refresh_palette()
            if event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if mx > self.w - self.ui_panel_width: # Over sidebar
                    self.palette_scroll_y = max(0, min(self.max_palette_scroll, self.palette_scroll_y - event.y * 30))
                else: # Over grid
                    self.zoom_level = max(0.2, min(4.0, self.zoom_level + event.y * 0.1))
            
            # Keyboard handling (Search & Shortcuts)
            if event.type == pygame.KEYDOWN:
                # 1. Ctrl Shortcuts (Priority)
                if event.mod & pygame.KMOD_CTRL:
                    if event.key == pygame.K_z: self.undo(); continue
                    if event.key == pygame.K_y: self.redo(); continue
                    if event.key == pygame.K_s: self.save_map(); continue
                    if event.key == pygame.K_c: self.copy_selection(); continue
                    if event.key == pygame.K_v: 
                        self.paste_mode = not self.paste_mode
                        self.status_message = "PASTE MODE " + ("ON" if self.paste_mode else "OFF")
                        self.status_timer = 60; continue
                    if event.key == pygame.K_x: self.cut_selection(); continue

                # 2. Escape Logic (Always active)
                if event.key == pygame.K_ESCAPE:
                    if self.show_weather_config: self.show_weather_config = False
                    elif self.search_active: self.search_active = False 
                    elif self.search_query: self.search_query = ""; self.refresh_palette()
                    elif self.metadata_focus: self.metadata_focus = False
                    else: self.show_confirmation("exit")
                    continue

                # 3. Metadata Input (Exclusive focus)
                if self.metadata_focus:
                    gx, gy = self.selection_start if self.selection_start else (0,0)
                    if event.key == pygame.K_BACKSPACE:
                        self.grid[gx][gy]["metadata"] = self.grid[gx][gy]["metadata"][:-1]
                    elif event.key == pygame.K_RETURN:
                        self.metadata_focus = False
                    elif event.unicode.isprintable():
                        self.grid[gx][gy]["metadata"] += event.unicode
                    continue

                # 4. Search Input (Priority if active)
                if self.search_active:
                    if event.key == pygame.K_BACKSPACE:
                        self.search_query = self.search_query[:-1]; self.refresh_palette()
                    elif event.unicode.isprintable():
                        self.search_query += event.unicode; self.refresh_palette()
                    continue

                # 5. Global Shortcuts & Nudging (Only if no focus)
                if not self.search_active and not self.metadata_focus:
                    if event.key == pygame.K_h: self.handle_menu_action("grid")
                    elif event.key == pygame.K_r: self.handle_menu_action("rotate")
                    elif event.key == pygame.K_x: self.handle_menu_action("clear")
                    elif event.key == pygame.K_g: self.handle_menu_action("shadow")
                    elif event.key == pygame.K_p: self.handle_menu_action("scatter")
                    elif event.key == pygame.K_f: self.handle_menu_action("flip_h")
                    elif event.key == pygame.K_v: self.handle_menu_action("flip_v")
                    elif event.key == pygame.K_5: self.handle_menu_action(LAYER_ANIM)
                    
                    # Nudging (REQ-DETAIL-01)
                    elif self.selection_start == self.selection_end and self.selection_start is not None:
                        gx, gy = self.selection_start
                        step = 1 if not (event.mod & pygame.KMOD_SHIFT) else 5
                        if event.key == pygame.K_UP: self.grid[gx][gy]["offset_y"] -= step
                        elif event.key == pygame.K_DOWN: self.grid[gx][gy]["offset_y"] += step
                        elif event.key == pygame.K_LEFT: self.grid[gx][gy]["offset_x"] -= step
                        elif event.key == pygame.K_RIGHT: self.grid[gx][gy]["offset_x"] += step
                        elif event.key == pygame.K_DELETE: self.grid[gx][gy]["offset_x"] = self.grid[gx][gy]["offset_y"] = 0

            if event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[0] and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    mx, my = pygame.mouse.get_pos()
                    gx, gy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                    if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                        self.selection_end = (gx, gy)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                # Handle dragging for selection
                if pygame.mouse.get_pressed()[0] and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    gx, gy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                    if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                        self.selection_end = (gx, gy)
                
                # Metadata Focus Check
                if self.selection_start == self.selection_end and self.selection_start:
                    y_meta = self.top_bar_height + 270 + 25
                    meta_r = pygame.Rect(self.w - self.ui_panel_width + 15, y_meta, self.ui_panel_width - 30, 25)
                    if meta_r.collidepoint(mx, my):
                        self.metadata_focus = True; self.search_active = False; return
                self.metadata_focus = False
                if self.active_menu:
                    m_root = next((b["rect"] for b in self.buttons if b["value"] == self.active_menu), None)
                    if m_root:
                        items = self.menu_items[self.active_menu]
                        for i, (text, val) in enumerate(items):
                            if text == "-": continue
                            if pygame.Rect(m_root.x, self.top_bar_height + i*25, 180, 25).collidepoint(mx, my):
                                self.handle_menu_action(val); self.active_menu = None; return
                    self.active_menu = None
                
                if self.confirm_target:
                    for b in self.modal_buttons:
                        if b["rect"].collidepoint(mx, my):
                            if b["value"]:
                                if self.confirm_target == "reset": self.save_snapshot(); self.grid = [[{k: (None if "id" in k else False) for k in self.grid[0][0].keys()} for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                                elif self.confirm_target == "exit": self.running = False
                            self.confirm_target = None; return
                
                if self.show_weather_config:
                    for b in self.weather_buttons:
                        if b["rect"].collidepoint(mx, my):
                            val = b["value"]
                            if val == "close": self.show_weather_config = False
                            elif val == "fog": self.show_fog = not self.show_fog
                            elif val == "fog_cycle": self.fog_color_idx = (self.fog_color_idx + 1) % len(self.fog_presets)
                            elif val == "rain": self.show_rain = not self.show_rain; self.init_rain()
                            elif val == "rain_floor": self.rain_collision_floor = not self.rain_collision_floor
                            elif val == "rain_obj": self.rain_collision_objects = not self.rain_collision_objects
                            elif val == "rain_splash": self.rain_splashes = not self.rain_splashes
                            elif val == "rain_density": 
                                self.rain_density = 500 if self.rain_density == 100 else (1000 if self.rain_density == 500 else 100)
                                self.init_rain()
                            elif val == "rain_angle": 
                                # Simulate slider: get mouse pos relative to button box
                                bx = b["rect"].x + 130
                                bw = 60
                                rel_x = (mx - bx) / bw
                                self.rain_angle = int(max(-10, min(10, (rel_x * 20.0) - 10)))
                            return
                    if not self.weather_rect.collidepoint(mx, my): self.show_weather_config = False; return
                    return
                
                # Check for Search Bar Focus (Panel area)
                panel_x = self.w - self.ui_panel_width
                search_y = self.top_bar_height + 150 # top_bar_height + 15 + (25*5) + 10
                search_rect = pygame.Rect(panel_x + 15, search_y, self.ui_panel_width - 30, 30)
                if search_rect.collidepoint(mx, my):
                    self.search_active = True
                elif mx < panel_x or my < self.top_bar_height:
                    self.search_active = False # Deactivate if clicking grid/menu

                # Sidebar Interaction check (Priority over Grid, but NOT over Top Bar)
                panel_x = self.w - self.ui_panel_width
                if mx >= panel_x and my >= self.top_bar_height:
                    found_btn = False
                    for b in self.buttons:
                        if b["rect"].collidepoint(mx, my):
                            if b["type"] == "menu_root": self.active_menu = b["value"] if self.active_menu != b["value"] else None
                            else: self.handle_menu_action(b["value"])
                            found_btn = True; break
                    
                    if not found_btn:
                        for b in self.palette_buttons:
                            if b["rect"].move(0, -self.palette_scroll_y).collidepoint(mx, my):
                                if my < self.top_bar_height + 360: continue 
                                if b["type"] == "category": self.current_cat = b["name"]; self.refresh_palette(); self.palette_scroll_y = 0
                                elif b["type"] == "back": self.current_cat = None; self.refresh_palette(); self.palette_scroll_y = 0
                                else: self.selected_item = b["name"]
                                found_btn = True; break
                    
                    # Deactivate search focus if clicking sidebar but NOT the search bar itself
                    search_y = self.top_bar_height + 150
                    search_rect = pygame.Rect(panel_x + 15, search_y, self.ui_panel_width - 30, 30)
                    if not search_rect.collidepoint(mx, my):
                        self.search_active = False
                    
                    if found_btn: return

                # Check top bar buttons (File, Edit, etc) if not caught by menu handling
                for b in self.buttons:
                    if b["type"] == "menu_root" and b["rect"].collidepoint(mx, my):
                        self.active_menu = b["value"] if self.active_menu != b["value"] else None
                        return

                gx, gy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                    if event.button == 1:
                        if pygame.key.get_mods() & pygame.KMOD_CTRL: # START SELECTION
                            self.selection_start = self.selection_end = (gx, gy)
                            self.metadata_focus = False
                            return
                        elif self.paste_mode: # PASTE
                            self.paste_at(gx, gy)
                            return
                        elif pygame.key.get_mods() & pygame.KMOD_SHIFT: # BUCKET FILL
                            self.bucket_fill(gx, gy)
                        elif self.current_layer == LAYER_COLLISION: 
                            self.save_snapshot(); self.grid[gx][gy]["collision"] = True
                        else:
                            self.save_snapshot()
                            self.selection_start = self.selection_end = (gx, gy)
                            
                            fw, fh = self.am.get_asset_footprint(self.selected_item, self.brush_rot)
                            sx, sy = gx - fw//2, gy - fh//2
                            key = "vfx" if self.current_layer == LAYER_ANIM else self.current_layer
                            self.grid[gx][gy][f"{key}_id"] = self.selected_item
                            
                            rotation = self.brush_rot
                            if self.brush_scatter:
                                import random
                                rotation = random.choice([0, 90, 180, 270])
                            
                            self.grid[gx][gy][f"{key}_rot"] = rotation
                            if self.current_layer == LAYER_OBJECTS:
                                self.grid[gx][gy]["objects_shadow"] = self.brush_shadow
                                for ix in range(fw):
                                    for iy in range(fh):
                                        if 0 <= sx+ix < GRID_SIZE and 0 <= sy+iy < GRID_SIZE: self.grid[sx+ix][sy+iy]["collision"] = True
                    elif event.button == 3:

                        self.save_snapshot()
                        if self.current_layer == LAYER_COLLISION: self.grid[gx][gy]["collision"] = False
                        else: self.grid[gx][gy][f"{self.current_layer}_id"] = None

    def run(self):
        self.ui.show_splash()
        while self.running:
            self.handle_events()
            keys = pygame.key.get_pressed()
            move_speed = 10 if keys[pygame.K_LSHIFT] else 5
            if keys[pygame.K_w] or keys[pygame.K_UP]: self.camera_offset.y += move_speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.camera_offset.y -= move_speed
            if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.camera_offset.x += move_speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.camera_offset.x -= move_speed
            
            self.screen.fill(BG_COLOR)
            zw, zh = TILE_W * self.zoom_level, TILE_H * self.zoom_level
            ticks = pygame.time.get_ticks()

            # Pass 1: Floor (LAYER_BASE) and Grid
            for x in range(GRID_SIZE):
                for y in range(GRID_SIZE):
                    sx, sy = world_to_screen(x, y, self.zoom_level, self.camera_offset)
                    if self.show_grid: pygame.draw.polygon(self.screen, GRID_COLOR, [(sx, sy), (sx+zw//2, sy+zh//2), (sx, sy+zh), (sx-zw//2, sy+zh//2)], 1)
                    
                    item_id = self.grid[x][y].get(f"{LAYER_BASE}_id")
                    if item_id:
                        for cat in self.am.assets[LAYER_BASE].values():
                            if item_id in cat:
                                img = cat[item_id]
                                iw, ih = int(zw), int(zh)
                                img_s = pygame.transform.scale(img, (max(1, iw), max(1, ih)))
                                if self.grid[x][y].get(f"{LAYER_BASE}_rot", 0) != 0:
                                    img_s = pygame.transform.rotate(img_s, -self.grid[x][y][f"{LAYER_BASE}_rot"])
                                # Apply Offset (REQ-DETAIL-01)
                                off_x, off_y = self.grid[x][y].get("offset_x", 0), self.grid[x][y].get("offset_y", 0)
                                self.screen.blit(img_s, (sx - zw//2 + off_x, sy + off_y))
                                break

            # Pass 2: Objects and VFX (Depth-correct over floors)
            for x in range(GRID_SIZE):
                for y in range(GRID_SIZE):
                    sx, sy = world_to_screen(x, y, self.zoom_level, self.camera_offset)
                    cell = self.grid[x][y]
                    for layer in [LAYER_OBJECTS, LAYER_VFX]:
                        item_id = cell.get(f"{layer}_id")
                        if not item_id: continue
                        
                        img = None
                        if item_id in self.am.animations:
                            frames = self.am.animations[item_id]
                            f_idx = (ticks // (1000 // ANIM_FPS)) % len(frames)
                            img = frames[f_idx]
                        else:
                            for cat in self.am.assets[layer].values():
                                if item_id in cat: img = cat[item_id]; break
                        
                        if img:
                            iw, ih = int(img.get_width()*self.zoom_level), int(img.get_height()*self.zoom_level)
                            img_s = pygame.transform.scale(img, (max(1, iw), max(1, ih)))
                            if cell.get(f"{layer}_rot", 0) != 0:
                                img_s = pygame.transform.rotate(img_s, -cell[f"{layer}_rot"])
                                
                            fw, fh = self.am.get_asset_footprint(item_id, cell.get(f"{layer}_rot", 0))
                            scx = (x - y) * (zw // 2) + self.camera_offset.x
                            anchor_y = (x + (fw - fw//2) + y + (fh - fh//2)) * (zh // 2) + self.camera_offset.y
                            
                            # Shadow Rendering
                            off_x, off_y = cell.get("offset_x", 0), cell.get("offset_y", 0)
                            if layer == LAYER_OBJECTS and cell.get("objects_shadow"):
                                shadow_surf = pygame.transform.scale(img_s, (img_s.get_width(), int(img_s.get_height() * 0.5)))
                                shadow_overlay = pygame.Surface(shadow_surf.get_size(), pygame.SRCALPHA)
                                shadow_overlay.fill((0, 0, 0, 100))
                                shadow_surf.blit(shadow_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                                self.screen.blit(shadow_surf, (scx - shadow_surf.get_width()//2 + off_x, anchor_y - shadow_surf.get_height() + off_y))

                            self.screen.blit(img_s, (scx - img_s.get_width()//2 + off_x, anchor_y - img_s.get_height() + off_y))

                    # Pass 3 Overlay: Coordinates (if zoom is close enough)
                    if self.zoom_level > 1.2:
                        coord_txt = self.font.render(f"{x},{y}", True, (80, 80, 100))
                        self.screen.blit(coord_txt, (sx - coord_txt.get_width()//2, sy + zh//2 - coord_txt.get_height()//2))

            # Draw Selection Overlay (REQ-EFF-04)
            if self.selection_start and self.selection_end:
                x1, y1 = self.selection_start
                x2, y2 = self.selection_end
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    for y in range(min(y1, y2), max(y1, y2) + 1):
                        sx, sy = world_to_screen(x, y, self.zoom_level, self.camera_offset)
                        pygame.draw.polygon(self.screen, (0, 255, 255), [(sx, sy), (sx+zw//2, sy+zh//2), (sx, sy+zh), (sx-zw//2, sy+zh//2)], 2)


            # Draw XYZ Axis Gizmo (REQ-VIS-02)
            axis_len = 60
            o_x, o_y = 100, self.h - 100
            iso_x = (1, 0.5); iso_y = (-1, 0.5); iso_z = (0, -1)
            pygame.draw.line(self.screen, (255, 50, 50), (o_x, o_y), (o_x + iso_x[0]*axis_len, o_y + iso_x[1]*axis_len), 2) # X
            pygame.draw.line(self.screen, (50, 255, 50), (o_x, o_y), (o_x + iso_y[0]*axis_len, o_y + iso_y[1]*axis_len), 2) # Y
            pygame.draw.line(self.screen, (50, 100, 255), (o_x, o_y), (o_x + iso_z[0]*axis_len, o_y + iso_z[1]*axis_len), 2) # Z
            self.screen.blit(self.bold_font.render("X", True, (255, 50, 50)), (o_x + iso_x[0]*axis_len + 5, o_y + iso_x[1]*axis_len))
            self.screen.blit(self.bold_font.render("Y", True, (50, 255, 50)), (o_x + iso_y[0]*axis_len - 15, o_y + iso_y[1]*axis_len))
            self.screen.blit(self.bold_font.render("Z", True, (50, 100, 255)), (o_x + iso_z[0]*axis_len - 10, o_y + iso_z[1]*axis_len - 20))
            
            # --- BRUSH PREVIEW & FOOTPRINT ---
            mx, my = pygame.mouse.get_pos()
            if mx < self.w - self.ui_panel_width and my > self.top_bar_height:
                bgx, bgy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                if 0 <= bgx < GRID_SIZE and 0 <= bgy < GRID_SIZE:
                    fw, fh = self.am.get_asset_footprint(self.selected_item, self.brush_rot)
                    sx_root, sy_root = bgx - fw//2, bgy - fh//2
                    
                    # Draw Blue Footprint (Malla azul)
                    for ix in range(fw):
                        for iy in range(fh):
                            tx, ty = sx_root+ix, sy_root+iy
                            if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                                psx, psy = world_to_screen(tx, ty, self.zoom_level, self.camera_offset)
                                pygame.draw.polygon(self.screen, HIGHLIGHT_COLOR, [(psx, psy), (psx+zw//2, psy+zh//2), (psx, psy+zh), (psx-zw//2, psy+zh//2)])
                    
                    # Item Preview (Semi-transparent)
                    if self.selected_item and self.current_layer != LAYER_COLLISION:
                        img_prev = None
                        if self.selected_item in self.am.animations: img_prev = self.am.animations[self.selected_item][0]
                        else:
                            for cat in self.am.assets.get(self.current_layer, {}).values():
                                if self.selected_item in cat: img_prev = cat[self.selected_item]; break
                        
                        if img_prev:
                            p_iw, p_ih = (int(zw), int(zh)) if self.current_layer == LAYER_BASE else (int(img_prev.get_width()*self.zoom_level), int(img_prev.get_height()*self.zoom_level))
                            p_img_s = pygame.transform.scale(img_prev, (max(1, p_iw), max(1, p_ih)))
                            if self.brush_rot != 0: p_img_s = pygame.transform.rotate(p_img_s, -self.brush_rot); p_img_s = pygame.transform.scale(p_img_s, (max(1, p_iw), max(1, p_ih)))
                            p_img_s.set_alpha(150)
                            
                            if self.current_layer == LAYER_BASE: self.screen.blit(p_img_s, (world_to_screen(bgx, bgy, self.zoom_level, self.camera_offset)[0] - zw//2, world_to_screen(bgx, bgy, self.zoom_level, self.camera_offset)[1]))
                            else:
                                p_scx = (bgx - bgy) * (zw // 2) + self.camera_offset.x
                                p_scy = (bgx + bgy) * (zh // 2) + self.camera_offset.y
                                self.screen.blit(p_img_s, (p_scx - p_img_s.get_width()//2, p_scy + zh//2 - p_img_s.get_height()))

            if self.status_timer > 0: self.status_timer -= 1
            
            # Draw Brush Preview (Blue Mesh + Ghost)
            self.ui.draw_brush_preview(*pygame.mouse.get_pos())
            
            # Weather Effects (On top of scene, below UI)
            self.draw_fog_effect()
            self.draw_rain_effect()
            
            self.ui.draw_menu_bar(); self.ui.draw_dropdowns(); self.ui.draw_sidebar(); self.ui.draw_modal(); self.ui.draw_weather_dialog(); self.ui.draw_status_message(); pygame.display.flip(); self.clock.tick(60)

    def update_ui_layout(self):
        self.buttons = []
        menu_x = 10
        for menu in self.menu_items.keys():
            txt = self.font.render(menu, True, TEXT_COLOR)
            rect = pygame.Rect(menu_x, 0, txt.get_width() + 20, self.top_bar_height)
            self.buttons.append({"rect": rect, "text": menu, "type": "menu_root", "value": menu})
            menu_x += rect.width + 5
        
        if self.ui_panel_width > 0:
            tools_y = self.top_bar_height + 145
            tool_btn_w = (self.ui_panel_width - 30) // 2
            tools = [("UNDO [Z]", "undo"), ("REDO [Y]", "redo"), ("ROTATE [R]", "rotate"), ("SHADOW [G]", "shadow"), ("SCATTER [P]", "scatter"), ("CLEAR [X]", "clear")]
            for i, (text, val) in enumerate(tools):
                bx = self.w - self.ui_panel_width + 10 + (i % 2) * (tool_btn_w + 10)
                by = tools_y + (i // 2) * 40
                self.buttons.append({"rect": pygame.Rect(bx, by, tool_btn_w, 30), "text": text, "type": "tool", "value": val})

        self.modal_rect = pygame.Rect(self.w//2 - 200, self.h//2 - 100, 400, 200)
        self.weather_rect = pygame.Rect(self.w//2 - 250, self.h//2 - 150, 500, 350)
        
    def show_confirmation(self, target):
        self.confirm_target = target
        self.modal_buttons = [
            {"rect": pygame.Rect(self.modal_rect.x + 50, self.modal_rect.y + 130, 120, 40), "text": "YES", "value": True},
            {"rect": pygame.Rect(self.modal_rect.x + 230, self.modal_rect.y + 130, 120, 40), "text": "NO", "value": False}
        ]

    def save_map(self):
        try:
            path = get_file_path(mode="save")
            if not path: return
            with open(path, 'w') as f:
                json.dump({
                    "version": VERSION, 
                    "grid": self.grid,
                    "weather": {
                        "fog": self.show_fog,
                        "fog_color_idx": self.fog_color_idx,
                        "rain": self.show_rain,
                        "rain_density": self.rain_density,
                        "rain_collision_floor": self.rain_collision_floor,
                        "rain_collision_objects": self.rain_collision_objects,
                        "rain_splashes": self.rain_splashes,
                        "rain_angle": self.rain_angle
                    }
                }, f)
            self.status_message = "MAP SAVED SUCCESSFULLY"
            self.status_timer = 180
        except Exception as e:
            self.status_message = f"ERROR SAVING MAP: {e}"
            self.status_timer = 180

    def load_map(self):
        try:
            path = get_file_path(mode="load")
            if not path: return
            with open(path, 'r') as f:
                data = json.load(f)
                
                # Check for legacy format (just a list of lists)
                if isinstance(data, list):
                    self.grid = data
                    self.status_message = "LEGACY MAP LOADED (NO VERSION)"
                    self.undo_stack.clear(); self.redo_stack.clear()
                # Check for current format (dictionary)
                elif isinstance(data, dict):
                    if "grid" not in data:
                        self.status_message = "LOADING ERROR: Missing 'grid' key"
                    else:
                        self.grid = data["grid"]
                        # Load Weather Settings
                        weather = data.get("weather", {})
                        self.show_fog = weather.get("fog", False)
                        self.fog_color_idx = weather.get("fog_color_idx", 0)
                        self.show_rain = weather.get("rain", False)
                        self.rain_density = weather.get("rain_density", 100)
                        self.rain_collision_floor = weather.get("rain_collision_floor", True)
                        self.rain_collision_objects = weather.get("rain_collision_objects", True)
                        self.rain_splashes = weather.get("rain_splashes", True)
                        self.rain_angle = weather.get("rain_angle", 0)
                        self.init_rain()
                        
                        if data.get("version") != VERSION:
                            self.status_message = f"V. MISMATCH: {data.get('version')} (Map) vs {VERSION}"
                        else:
                            self.status_message = "MAP LOADED SUCCESSFULLY"
                        self.undo_stack.clear(); self.redo_stack.clear()
                else:
                    self.status_message = "FORMAT ERROR: Invalid structure"
            self.status_timer = 300 # Longer duration for warnings
        except json.JSONDecodeError:
            self.status_message = "FILE ERROR: Corrupted or invalid JSON"
            self.status_timer = 180
        except Exception as e:
            self.status_message = f"LOAD ERROR: {str(e)}"
            self.status_timer = 180

    def handle_menu_action(self, val):
        if val in [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, LAYER_COLLISION, LAYER_ANIM]: 
            self.current_layer = val; self.current_cat = None; self.refresh_palette()
        elif val == "undo": self.undo()
        elif val == "redo": self.redo()
        elif val == "reset": self.show_confirmation("reset")
        elif val == "load": self.load_map()
        elif val == "save": self.save_map()
        elif val == "config": 
            if self.cm.change_asset_paths(): self.am.load_assets(self.cm.config); self.refresh_palette()
        elif val == "exit": self.show_confirmation("exit")
        elif val == "flip_h": self.brush_fh = not self.brush_fh
        elif val == "flip_v": self.brush_fv = not self.brush_fv
        elif val == "rotate": 
            self.brush_rot = (self.brush_rot + 90) % 360
            self.status_message = f"ROTATION: {self.brush_rot}°"
            self.status_timer = 60
        elif val == "shadow": 
            self.brush_shadow = not self.brush_shadow
            self.status_message = f"SHADOWS {'ON' if self.brush_shadow else 'OFF'}"
            self.status_timer = 60
        elif val == "scatter":
            self.brush_scatter = not self.brush_scatter
            self.status_message = f"SCATTER BRUSH {'ON' if self.brush_scatter else 'OFF'}"
            self.status_timer = 60
        elif val == "clear": 
            self.brush_fh = self.brush_fv = self.brush_shadow = self.brush_scatter = False; self.brush_rot = 0
            self.status_message = "BRUSH RESET"
            self.status_timer = 60
        elif val == "grid": self.show_grid = not self.show_grid
        elif val == "sidebar": self.ui_panel_width = 250 if self.ui_panel_width == 0 else 0; self.update_ui_layout()
        elif val == "fog": 
            self.show_fog = not self.show_fog
            self.status_message = f"FOG {'ON' if self.show_fog else 'OFF'}"
            self.status_timer = 60
        elif val == "fog_cycle":
            self.fog_color_idx = (self.fog_color_idx + 1) % len(self.fog_presets)
            self.status_message = f"FOG COLOR CHANGED ({self.fog_color_idx + 1}/{len(self.fog_presets)})"
            self.status_timer = 60
        elif val == "weather_config": self.show_weather_settings()

    def show_weather_settings(self):
        self.show_weather_config = True
        self.weather_buttons = []
        r = self.weather_rect
        btn_w, btn_h = 200, 30
        x1, x2 = r.x + 20, r.x + 270
        y_start = r.y + 60
        
        settings = [
            ("Fog Enabled", "fog"), ("Fog Color", "fog_cycle"),
            ("Rain Enabled", "rain"), ("Rain Density", "rain_density"),
            ("Floor Collision", "rain_floor"), ("Object Collision", "rain_obj"),
            ("Show Splashes", "rain_splash"), ("Rain Direction", "rain_angle")
        ]
        
        for i, (text, val) in enumerate(settings):
            bx = x1 if i % 2 == 0 else x2
            by = y_start + (i // 2) * 50
            self.weather_buttons.append({"rect": pygame.Rect(bx, by, btn_w, btn_h), "text": text, "value": val})
            
        self.weather_buttons.append({
            "rect": pygame.Rect(r.centerx - 60, r.bottom - 50, 120, 40),
            "text": "CLOSE", "value": "close"
        })

