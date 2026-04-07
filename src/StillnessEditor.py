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
        self.top_bar_height = UI_TOP_BAR_H
        self.camera_offset = pygame.Vector2(self.w // 2, self.h // 4 + self.top_bar_height)
        self.show_grid = True
        self.active_menu = None
        self.confirm_target = None
        self.modal_buttons = []
        self.status_message = None
        self.status_timer = 0
        self.search_active = False # REQ-EFF-03 (Focus)
        self.palette_scroll_y = 0
        self.max_palette_scroll = 0
        
        # New Redesign State (v2.0)
        self.active_tab = "scene" # "scene", "assets", "inspector"
        self.active_tool = "brush"   # "select", "brush", "bucket", "fog", "eraser"
        self.ui_rects = {}
        
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
        
        # Professional Fog Zones (REQ-FOG-01)
        self.fog_zones = []
        self.selected_fog_idx = -1
        self.fog_draw_start = None
        self.fog_tool_active = False # True when Fog Zone tool is picked

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

    def init_fog_puffs(self, zone):
        """Generates procedural mist particles for a specific zone."""
        import random
        # Number of puffs scales with zone density and area
        area = zone["size"][0] * zone["size"][1]
        count = int(DEFAULT_PUFF_COUNT * zone.get("density", DEFAULT_FOG_DENSITY) * (area ** 0.5))
        zone["puffs"] = []
        for _ in range(max(5, count)):
            zone["puffs"].append({
                "rel_x": random.uniform(0, 1),
                "rel_y": random.uniform(0, 1),
                "size_mult": random.uniform(0.8, 1.5),
                "vx": random.uniform(0.001, 0.003),
                "vy": random.uniform(-0.001, 0.001)
            })

    def update_fog_zones(self):
        """Drifts fog puffs and handles wrapping."""
        for zone in self.fog_zones:
            speed = zone.get("speed", DEFAULT_FOG_SPEED)
            for p in zone["puffs"]:
                p["rel_x"] += p["vx"] * speed
                p["rel_y"] += p["vy"] * speed
                if p["rel_x"] > 1.1: p["rel_x"] = -0.1
                if p["rel_x"] < -0.1: p["rel_x"] = 1.1
                if p["rel_y"] > 1.1: p["rel_y"] = -0.1
                if p["rel_y"] < -0.1: p["rel_y"] = 1.1

    def draw_fog_effect(self):
        # 1. Global Fog (Legacy/Toggle)
        if self.show_fog:
            fog_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            color = self.fog_presets[self.fog_color_idx]
            fog_surf.fill((*color, 80)) 
            self.screen.blit(fog_surf, (0, 0))

        # 2. Professional Fog Zones
        if not self.fog_zones: return
        
        zw, zh = TILE_W * self.zoom_level, TILE_H * self.zoom_level
        
        for idx, zone in enumerate(self.fog_zones):
            z_pos = zone["pos"]
            z_size = zone["size"]
            z_color = zone.get("color", DEFAULT_FOG_COLOR)
            z_feather = zone.get("feather", DEFAULT_FOG_FEATHER)
            base_alpha = int(zone.get("density", DEFAULT_FOG_DENSITY) * 120)
            
            for p in zone["puffs"]:
                wx, wy = z_pos[0] + p["rel_x"] * z_size[0], z_pos[1] + p["rel_y"] * z_size[1]
                psx, psy = world_to_screen(wx, wy, self.zoom_level, self.camera_offset)
                
                # Culling
                if not (-200 < psx < self.w + 200 and -200 < psy < self.h + 200): continue
                
                # Alpha Feathering
                rx, ry = p["rel_x"], p["rel_y"]
                fade = 1.0
                if zone.get("shape") == FOG_SHAPE_RECT:
                    fade = min(rx, 1.0-rx, ry, 1.0-ry) / max(0.01, z_feather)
                else:
                    dist = ((rx-0.5)**2 + (ry-0.5)**2)**0.5 * 2
                    fade = (1.0 - dist) / max(0.01, z_feather)
                
                final_alpha = int(base_alpha * max(0.0, min(1.0, fade)))
                if final_alpha <= 5: continue
                
                puff_size = int(64 * self.zoom_level * p["size_mult"])
                # Procedural Puff Drawing (Optimized)
                # Note: For production use a pre-rendered radial sprite
                ps = pygame.Surface((puff_size*2, puff_size*2), pygame.SRCALPHA)
                pygame.draw.circle(ps, (*z_color, final_alpha), (puff_size, puff_size), puff_size)
                self.screen.blit(ps, (psx - puff_size, psy - puff_size), special_flags=pygame.BLEND_RGBA_ADD)

            # Editor Visualizer (Selected)
            if idx == self.selected_fog_idx:
                pts = [world_to_screen(z_pos[0], z_pos[1], self.zoom_level, self.camera_offset),
                       world_to_screen(z_pos[0]+z_size[0], z_pos[1], self.zoom_level, self.camera_offset),
                       world_to_screen(z_pos[0]+z_size[0], z_pos[1]+z_size[1], self.zoom_level, self.camera_offset),
                       world_to_screen(z_pos[0], z_pos[1]+z_size[1], self.zoom_level, self.camera_offset)]
                pygame.draw.lines(self.screen, (255, 255, 100), True, pts, 2)

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
        
        # New workbench layout positioning
        x_start = self.w - UI_RIGHT_SIDEBAR_W + 10
        y_start = UI_TOP_BAR_H + UI_TAB_H + 55 # Below tab and search bar
        thumb_w, thumb_h = (UI_RIGHT_SIDEBAR_W - 30) // 2, 60
        
        # Filtering logic
        if self.current_layer == LAYER_ANIM:
            assets = {k: v for k, v in self.am.assets[LAYER_ANIM].items() if self.search_query.lower() in k.lower()}
            for i, (name, img) in enumerate(assets.items()):
                rect = pygame.Rect(x_start + (i%2)*(thumb_w + 10), y_start + (i//2)*(thumb_h + 10), thumb_w, thumb_h)
                self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img, "anim": True})
        else:
            assets = self.am.assets[self.current_layer]
            if self.current_layer == LAYER_BASE:
                items = {k: v for k, v in assets.get("main", {}).items() if self.search_query.lower() in k.lower()}
                for i, (name, img) in enumerate(items.items()):
                    rect = pygame.Rect(x_start + (i%2)*(thumb_w + 10), y_start + (i//2)*(thumb_h + 10), thumb_w, thumb_h)
                    self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img})
            elif not self.current_cat:
                for i, cat in enumerate(assets):
                    rect = pygame.Rect(x_start + (i%2)*(thumb_w + 10), y_start + (i//2)*(thumb_h + 10), thumb_w, thumb_h)
                    self.palette_buttons.append({"rect": rect, "name": cat, "type": "category"})
            else:
                raw_items = assets.get(self.current_cat, {})
                items = {k: v for k, v in raw_items.items() if self.search_query.lower() in k.lower()}
                display_items = [(".. BACK", None)] + list(items.items())
                for i, (name, img) in enumerate(display_items):
                    rect = pygame.Rect(x_start + (i%2)*(thumb_w + 10), y_start + (i//2)*(thumb_h + 10), thumb_w, thumb_h)
                    if name == ".. BACK": self.palette_buttons.append({"rect": rect, "name": name, "type": "back"})
                    else: self.palette_buttons.append({"rect": rect, "name": name, "type": "item", "img": img})
        
        # Calculate Max Scroll
        visible_h = self.h - (y_start + UI_BOTTOM_BAR_H + 10)
        total_h = ((len(self.palette_buttons) + 1) // 2) * (thumb_h + 10)
        self.max_palette_scroll = max(0, total_h - visible_h + 40)

    def handle_events(self):
        mx, my = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.VIDEORESIZE:
                self.w, self.h = event.w, event.h
                self.update_ui_layout()
                self.refresh_palette()

            # 1. MODAL OVERLAY PRIORITY
            if self.confirm_target:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for b in self.modal_buttons:
                        if b["rect"].collidepoint(mx, my):
                            if b["value"]:
                                if self.confirm_target == "reset": 
                                    self.save_snapshot()
                                    self.grid = [[{k: (None if "id" in k else (0 if "offset" in k else ("" if k=="metadata" else False))) for k in self.grid[0][0].keys()} for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                                elif self.confirm_target == "exit": self.running = False
                            self.confirm_target = None
                continue

            # 2. DROPDOWN PRIORITY
            if self.active_menu:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    m_root = next((b["rect"] for b in self.buttons if b["value"] == self.active_menu), None)
                    if m_root:
                        items = self.menu_items[self.active_menu]
                        for i, (text, val) in enumerate(items):
                            if text == "-": continue
                            if pygame.Rect(m_root.x, UI_TOP_BAR_H + i*25, 180, 25).collidepoint(mx, my):
                                self.handle_menu_action(val)
                    self.active_menu = None
                    continue

            # 3. KEYBOARD shorthands
            if event.type == pygame.KEYDOWN:
                if self.metadata_focus: self.handle_metadata_input(event); continue
                if self.search_active: self.handle_search_input(event); continue
                
                if event.mod & pygame.KMOD_CTRL:
                    if event.key == pygame.K_z: self.undo(); continue
                    if event.key == pygame.K_y: self.redo(); continue
                    if event.key == pygame.K_s: self.save_map(); continue
                    if event.key == pygame.K_c: self.copy_selection(); continue
                    if event.key == pygame.K_v: self.paste_mode = not self.paste_mode; continue
                    if event.key == pygame.K_x: self.cut_selection(); continue
                
                if event.key == pygame.K_ESCAPE:
                    if self.search_query: self.search_query = ""; self.refresh_palette()
                    else: self.show_confirmation("exit")
                    continue
                
            # 4. MOUSE DISPATCHING
            if event.type == pygame.MOUSEWHEEL:
                if self.ui_rects["right_sidebar"].collidepoint(mx, my):
                    self.palette_scroll_y = max(0, min(self.max_palette_scroll, self.palette_scroll_y - event.y * 30))
                else:
                    self.zoom_level = max(0.2, min(4.0, self.zoom_level + event.y * 0.1))

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.ui_rects["top_bar"].collidepoint(mx, my):
                    for b in self.buttons:
                        if b["type"] == "menu_root" and b["rect"].collidepoint(mx, my):
                            self.active_menu = b["value"]; return
                
                elif self.ui_rects["left_toolbar"].collidepoint(mx, my):
                    for b in self.buttons:
                        if b["type"] == "tool" and b["rect"].collidepoint(mx, my):
                            self.active_tool = b["value"]
                            if b["value"] in ["brush", "bucket"]: self.active_tab = "assets"
                            return

                elif self.ui_rects["right_sidebar"].collidepoint(mx, my):
                    self.handle_sidebar_click(mx, my, event.button)
                
                elif self.ui_rects["viewport"].collidepoint(mx, my):
                    self.handle_viewport_click(mx, my, event.button)

            if event.type == pygame.MOUSEMOTION:
                if pygame.mouse.get_pressed()[0] and self.active_tool == "select":
                    if self.ui_rects["viewport"].collidepoint(mx, my):
                        gx, gy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                        if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                            self.selection_end = (gx, gy)

    def handle_metadata_input(self, event):
        if not self.selection_start: return
        gx, gy = self.selection_start
        if event.key == pygame.K_BACKSPACE: self.grid[gx][gy]["metadata"] = self.grid[gx][gy]["metadata"][:-1]
        elif event.key == pygame.K_RETURN: self.metadata_focus = False
        elif event.unicode.isprintable(): self.grid[gx][gy]["metadata"] += event.unicode

    def handle_search_input(self, event):
        if event.key == pygame.K_BACKSPACE: self.search_query = self.search_query[:-1]; self.refresh_palette()
        elif event.key == pygame.K_RETURN: self.search_active = False
        elif event.unicode.isprintable(): self.search_query += event.unicode; self.refresh_palette()

    def handle_sidebar_click(self, mx, my, button):
        # 1. Tabs
        for b in self.buttons:
            if b["type"] == "tab" and b["rect"].collidepoint(mx, my):
                self.active_tab = b["value"]; return

        # 2. Content
        if self.active_tab == "assets":
            search_y = UI_TOP_BAR_H + UI_TAB_H + 10
            search_rect = pygame.Rect(self.w - UI_RIGHT_SIDEBAR_W + 10, search_y, UI_RIGHT_SIDEBAR_W - 20, 30)
            if search_rect.collidepoint(mx, my): self.search_active = True; return
            self.search_active = False
            
            for b in self.palette_buttons:
                p_rect = b["rect"].copy()
                p_rect.y -= self.palette_scroll_y
                if p_rect.collidepoint(mx, my):
                    if b["type"] == "category": self.current_cat = b["name"]; self.refresh_palette(); self.palette_scroll_y = 0
                    elif b["type"] == "back": self.current_cat = None; self.refresh_palette(); self.palette_scroll_y = 0
                    else: self.selected_item = b["name"]
                    return

        elif self.active_tab == "inspector":
            if self.selection_start:
                meta_y = UI_TOP_BAR_H + UI_TAB_H + 140
                meta_rect = pygame.Rect(self.w - UI_RIGHT_SIDEBAR_W + 10, meta_y, UI_RIGHT_SIDEBAR_W - 20, 28)
                if meta_rect.collidepoint(mx, my): self.metadata_focus = True; return
            self.metadata_focus = False

            if self.selected_fog_idx != -1:
                y_fz = UI_TOP_BAR_H + UI_TAB_H + 200
                props = ["toggle_shape", "adj_density", "adj_feather", "delete_zone"]
                for i, p_val in enumerate(props):
                    rect = pygame.Rect(self.w - UI_RIGHT_SIDEBAR_W + 10, y_fz + i*28, UI_RIGHT_SIDEBAR_W - 20, 24)
                    if rect.collidepoint(mx, my):
                        fz = self.fog_zones[self.selected_fog_idx]
                        if p_val == "toggle_shape": fz["shape"] = FOG_SHAPE_RECT if fz.get("shape") == FOG_SHAPE_ELLIPSE else FOG_SHAPE_ELLIPSE
                        elif p_val == "adj_density": fz["density"] = (fz.get("density", 0.5) % 1.0) + 0.1; self.init_fog_puffs(fz)
                        elif p_val == "adj_feather": fz["feather"] = (fz.get("feather", 0.25) + 0.05) if fz.get("feather", 0.25) < 0.5 else 0.05
                        elif p_val == "delete_zone": self.fog_zones.pop(self.selected_fog_idx); self.selected_fog_idx = -1
                        return

        elif self.active_tab == "scene":
            y_l = UI_TOP_BAR_H + UI_TAB_H + 35
            layers = [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, LAYER_COLLISION, LAYER_ANIM]
            for i, l in enumerate(layers):
                btn_r = pygame.Rect(self.w - UI_RIGHT_SIDEBAR_W + 10, y_l + i*28, UI_RIGHT_SIDEBAR_W - 20, 24)
                if btn_r.collidepoint(mx, my): self.current_layer = l; self.refresh_palette(); return
            
            y_e = y_l + (5 * 28) + 40
            t_vals = [("grid", "show_grid"), ("fog", "show_fog"), ("rain", "show_rain")]
            for i, (v, attr) in enumerate(t_vals):
                btn_r = pygame.Rect(self.w - UI_RIGHT_SIDEBAR_W + 10, y_e + i*28, UI_RIGHT_SIDEBAR_W - 20, 24)
                if btn_r.collidepoint(mx, my):
                    setattr(self, attr, not getattr(self, attr))
                    if v == "rain": self.init_rain()
                    return

    def handle_viewport_click(self, mx, my, button):
        gx, gy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
        if not (0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE): return
        
        if button == 3 or self.active_tool == "eraser":
            self.save_snapshot()
            key = "vfx" if self.current_layer == LAYER_ANIM else self.current_layer
            if self.current_layer == LAYER_COLLISION: self.grid[gx][gy]["collision"] = False
            else: self.grid[gx][gy][f"{key}_id"] = None
            return

        if button == 1:
            if self.active_tool == "select":
                for idx, zone in enumerate(self.fog_zones):
                    z_pos, z_sz = zone["pos"], zone["size"]
                    if z_pos[0] <= gx <= z_pos[0]+z_sz[0] and z_pos[1] <= gy <= z_pos[1]+z_sz[1]:
                        self.selected_fog_idx = idx; self.active_tab = "inspector"; return
                self.selection_start = self.selection_end = (gx, gy); self.selected_fog_idx = -1; self.active_tab = "inspector"
            elif self.active_tool == "brush":
                if not self.selected_item: return
                self.save_snapshot()
                key = "vfx" if self.current_layer == LAYER_ANIM else self.current_layer
                self.grid[gx][gy][f"{key}_id"] = self.selected_item
                self.grid[gx][gy][f"{key}_rot"] = self.brush_rot
                if self.current_layer == LAYER_OBJECTS: self.grid[gx][gy]["objects_shadow"] = self.brush_shadow
            elif self.active_tool == "bucket":
                if not self.selected_item: return
                self.bucket_fill(gx, gy)
            elif self.active_tool == "fog":
                self.fog_draw_start = (gx, gy)

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
            
            if self.status_timer > 0: self.status_timer -= 1
            
            # --- VIEWPORT UI & EFFECTS ---
            if self.ui_rects["viewport"].collidepoint(pygame.mouse.get_pos()):
                self.ui.draw_brush_preview(*pygame.mouse.get_pos())
            
            # Fog Zone Creation Preview
            if self.fog_draw_start:
                mx, my = pygame.mouse.get_pos()
                mwx, mwy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                z_pos = (min(self.fog_draw_start[0], mwx), min(self.fog_draw_start[1], mwy))
                z_size = (max(1, abs(self.fog_draw_start[0] - mwx)), max(1, abs(self.fog_draw_start[1] - mwy)))
                pts = [world_to_screen(z_pos[0], z_pos[1], self.zoom_level, self.camera_offset),
                       world_to_screen(z_pos[0]+z_size[0], z_pos[1], self.zoom_level, self.camera_offset),
                       world_to_screen(z_pos[0]+z_size[0], z_pos[1]+z_size[1], self.zoom_level, self.camera_offset),
                       world_to_screen(z_pos[0], z_pos[1]+z_size[1], self.zoom_level, self.camera_offset)]
                pygame.draw.lines(self.screen, ACCENT_COLOR, True, pts, 2)

            self.update_fog_zones()
            self.draw_fog_effect()
            self.draw_rain_effect()
            
            # --- FINAL UI LAYER ---
            self.ui.draw_menu_bar()
            self.ui.draw_dropdowns()
            self.ui.draw_left_toolbar()
            self.ui.draw_right_sidebar()
            self.ui.draw_bottom_bar()
            self.ui.draw_modal()
            self.ui.draw_status_message()
            
            pygame.display.flip()
            self.clock.tick(60)

    def update_ui_layout(self):
        """Calculates all UI panel rectangles and button positions for the v2.0 workbench."""
        self.ui_rects = {
            "top_bar": pygame.Rect(0, 0, self.w, UI_TOP_BAR_H),
            "left_toolbar": pygame.Rect(0, UI_TOP_BAR_H, UI_LEFT_TOOLBAR_W, self.h - UI_TOP_BAR_H - UI_BOTTOM_BAR_H),
            "right_sidebar": pygame.Rect(self.w - UI_RIGHT_SIDEBAR_W, UI_TOP_BAR_H, UI_RIGHT_SIDEBAR_W, self.h - UI_TOP_BAR_H - UI_BOTTOM_BAR_H),
            "bottom_bar": pygame.Rect(0, self.h - UI_BOTTOM_BAR_H, self.w, UI_BOTTOM_BAR_H),
            "viewport": pygame.Rect(UI_LEFT_TOOLBAR_W, UI_TOP_BAR_H, self.w - UI_LEFT_TOOLBAR_W - UI_RIGHT_SIDEBAR_W, self.h - UI_TOP_BAR_H - UI_BOTTOM_BAR_H)
        }

        self.buttons = []
        # 1. Top Bar Menus
        menu_x = 10
        for menu in ["FILE", "EDIT", "VIEW", "LAYER"]:
            txt = self.font.render(menu, True, (255, 255, 255))
            r = pygame.Rect(menu_x, (UI_TOP_BAR_H - 24)//2, txt.get_width() + 20, 24)
            self.buttons.append({"rect": r, "text": menu, "value": menu, "type": "menu_root"})
            menu_x += r.width + 5

        # 2. Left Toolbar Tools
        tools = [
            ("S", "select", "Select & Inspector (S)"), 
            ("B", "brush", "Brush Tool (B)"), 
            ("F", "bucket", "Bucket Fill (F)"), 
            ("G", "fog", "Fog Zone Tool (G)"), 
            ("E", "eraser", "Eraser Tool (E)")
        ]
        for i, (icon, val, caption) in enumerate(tools):
            r = pygame.Rect((UI_LEFT_TOOLBAR_W - UI_TOOL_ICON_SIZE)//2, UI_TOP_BAR_H + 10 + i*(UI_TOOL_ICON_SIZE + 10), UI_TOOL_ICON_SIZE, UI_TOOL_ICON_SIZE)
            self.buttons.append({"rect": r, "text": icon, "value": val, "type": "tool", "caption": caption})

        # 3. Right Sidebar Tabs
        tab_w = UI_RIGHT_SIDEBAR_W // 3
        for i, tab in enumerate(["scene", "assets", "inspector"]):
            r = pygame.Rect(self.ui_rects["right_sidebar"].x + i*tab_w, UI_TOP_BAR_H, tab_w, UI_TAB_H)
            self.buttons.append({"rect": r, "text": tab.upper(), "value": tab, "type": "tab"})

        # 4. Modals and Shared UI
        self.modal_rect = pygame.Rect(self.w//2 - 200, self.h//2 - 100, 400, 200)
        self.modal_buttons = [
            {"rect": pygame.Rect(self.modal_rect.x + 50, self.modal_rect.y + 130, 100, 40), "text": "YES", "value": True},
            {"rect": pygame.Rect(self.modal_rect.x + 250, self.modal_rect.y + 130, 100, 40), "text": "NO", "value": False}
        ]
        
        self.weather_rect = pygame.Rect(self.w//2 - 150, self.h//2 - 200, 300, 410)
        # Weather buttons will be dynamically drawn in the Scene tab or as a fallback
        
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
                        "fog_zones": [{k: v for k, v in fz.items() if k != "puffs"} for fz in self.fog_zones],
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
                        self.fog_zones = weather.get("fog_zones", [])
                        for fz in self.fog_zones: self.init_fog_puffs(fz)
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
        elif val == "fog_tool":
            self.fog_tool_active = not self.fog_tool_active
            self.status_message = "FOG TOOL " + ("ON" if self.fog_tool_active else "OFF")
            self.status_timer = 60
            if self.fog_tool_active: self.selected_item = None # Deselect brushes

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

