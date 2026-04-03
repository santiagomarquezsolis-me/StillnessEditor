import pygame
import sys
import os
import json
from collections import deque
import copy
from .constants import *
from .utils import world_to_screen, screen_to_world, get_file_path
from .config_manager import ConfigManager
from .asset_manager import AssetManager
from .ui_renderer import UIRenderer

class StillnessEditor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
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
        self.brush_fh = self.brush_fv = self.brush_shadow = False
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
        
        # History (REQ-EFF-01)
        self.undo_stack = deque(maxlen=UNDO_LIMIT)
        self.redo_stack = deque(maxlen=UNDO_LIMIT)

        self.menu_items = {
            "FILE": [("New Map", "reset"), ("Open...", "load"), ("Save As...", "save"), ("Configuration", "config"), ("-", ""), ("Exit", "exit")],
            "EDIT": [("Undo [Ctrl+Z]", "undo"), ("Redo [Ctrl+Y]", "redo"), ("-", ""), ("Flip H [F]", "flip_h"), ("Flip V [V]", "flip_v"), ("Rotate [R]", "rotate"), ("Reset [X]", "clear")],
            "VIEW": [("Toggle Grid [H]", "grid"), ("Toggle Sidebar", "sidebar"), ("Fullscreen [F11]", "fs")],
            "LAYER": [("Base [1]", LAYER_BASE), ("Objects [2]", LAYER_OBJECTS), ("VFX [3]", LAYER_VFX), ("Collision [4]", LAYER_COLLISION), ("Animations [5]", LAYER_ANIM)]
        }

        self.grid = [[{
            "base_id": None, "base_fh": False, "base_fv": False, "base_rot": 0,
            "objects_id": None, "objects_fh": False, "objects_fv": False, "objects_rot": 0, "objects_shadow": False,
            "vfx_id": None, "vfx_fh": False, "vfx_fv": False, "vfx_rot": 0,
            "collision": False
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

    def bucket_fill(self, start_x, start_y):
        """Fills contiguous area of same base_id with selected_item."""
        if self.current_layer != LAYER_BASE or not self.selected_item: return
        target_id = self.grid[start_x][start_y]["base_id"]
        if target_id == self.selected_item: return
        
        self.save_snapshot()
        queue = deque([(start_x, start_y)])
        visited = set([(start_x, start_y)])
        
        while queue:
            x, y = queue.popleft()
            self.grid[x][y]["base_id"] = self.selected_item
            
            for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    if (nx, ny) not in visited and self.grid[nx][ny]["base_id"] == target_id:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        self.status_message = "BUCKET FILL APPLIED"
        self.status_timer = 120

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
                if event.mod & pygame.KMOD_CTRL:
                    if event.key == pygame.K_z: self.undo()
                    if event.key == pygame.K_y: self.redo()
                    if event.key == pygame.K_s: self.save_map()
                else:
                    if event.key == pygame.K_BACKSPACE and self.search_active: self.search_query = self.search_query[:-1]; self.refresh_palette()
                    elif event.key == pygame.K_ESCAPE:
                        if self.search_active: self.search_active = False # Deactivate on ESC
                        elif self.search_query: self.search_query = ""; self.refresh_palette()
                        else: self.show_confirmation("exit")
                    
                    # Search input (if focused and no system key)
                    elif self.search_active and event.unicode.isprintable():
                        self.search_query += event.unicode
                        self.refresh_palette()
                        return # Stop here if searching
                    
                    # Global Shortcuts (Priority over Search if no focus)
                    elif not self.search_active:
                        if event.key == pygame.K_h: self.handle_menu_action("grid")
                        elif event.key == pygame.K_r: self.handle_menu_action("rotate")
                        elif event.key == pygame.K_x: self.handle_menu_action("clear")
                        elif event.key == pygame.K_g: self.handle_menu_action("shadow")
                        elif event.key == pygame.K_f: self.handle_menu_action("flip_h")
                        elif event.key == pygame.K_v: self.handle_menu_action("flip_v")
                        
                        # Layer shortcuts
                        elif event.key == pygame.K_1: self.handle_menu_action(LAYER_BASE)
                        elif event.key == pygame.K_2: self.handle_menu_action(LAYER_OBJECTS)
                        elif event.key == pygame.K_3: self.handle_menu_action(LAYER_VFX)
                        elif event.key == pygame.K_4: self.handle_menu_action(LAYER_COLLISION)
                        elif event.key == pygame.K_5: self.handle_menu_action(LAYER_ANIM)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                # Menu / Modal handling ...
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
                
                # Check for Search Bar Focus (Panel area)
                panel_x = self.w - self.ui_panel_width
                search_y = self.top_bar_height + 150 # top_bar_height + 15 + (25*5) + 10
                search_rect = pygame.Rect(panel_x + 15, search_y, self.ui_panel_width - 30, 30)
                if search_rect.collidepoint(mx, my):
                    self.search_active = True
                elif mx < panel_x or my < self.top_bar_height:
                    self.search_active = False # Deactivate if clicking grid/menu

                for b in self.buttons:
                    if b["rect"].collidepoint(mx, my):
                        if b["type"] == "menu_root": self.active_menu = b["value"] if self.active_menu != b["value"] else None
                        else: self.handle_menu_action(b["value"])
                        return

                for b in self.palette_buttons:
                    # Adjust collision check with scroll offset
                    if b["rect"].move(0, -self.palette_scroll_y).collidepoint(mx, my):
                        # Ensure we don't click items that are obscured by the top part of the sidebar
                        if my < self.top_bar_height + 360: continue 
                        if b["type"] == "category": self.current_cat = b["name"]; self.refresh_palette(); self.palette_scroll_y = 0
                        elif b["type"] == "back": self.current_cat = None; self.refresh_palette(); self.palette_scroll_y = 0
                        else: self.selected_item = b["name"]
                        return

                gx, gy = screen_to_world(mx, my, self.zoom_level, self.camera_offset)
                if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
                    if event.button == 1:
                        if pygame.key.get_mods() & pygame.KMOD_SHIFT: # BUCKET FILL
                            self.bucket_fill(gx, gy)
                        elif self.current_layer == LAYER_COLLISION: 
                            self.save_snapshot(); self.grid[gx][gy]["collision"] = True
                        else:
                            self.save_snapshot()
                            fw, fh = self.am.get_asset_footprint(self.selected_item, self.brush_rot)
                            sx, sy = gx - fw//2, gy - fh//2
                            key = "vfx" if self.current_layer == LAYER_ANIM else self.current_layer
                            self.grid[gx][gy][f"{key}_id"] = self.selected_item
                            self.grid[gx][gy][f"{key}_rot"] = self.brush_rot
                            if self.current_layer == LAYER_OBJECTS:
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

            for x in range(GRID_SIZE):
                for y in range(GRID_SIZE):
                    sx, sy = world_to_screen(x, y, self.zoom_level, self.camera_offset)
                    if self.show_grid: pygame.draw.polygon(self.screen, GRID_COLOR, [(sx, sy), (sx+zw//2, sy+zh//2), (sx, sy+zh), (sx-zw//2, sy+zh//2)], 1)
                    cell = self.grid[x][y]
                    for layer in [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX]:
                        item_id = cell.get(f"{layer}_id")
                        if not item_id: continue
                        
                        # Animation Logic
                        img = None
                        if item_id in self.am.animations:
                            frames = self.am.animations[item_id]
                            f_idx = (ticks // (1000 // ANIM_FPS)) % len(frames)
                            img = frames[f_idx]
                        else:
                            for cat in self.am.assets[layer].values():
                                if item_id in cat: img = cat[item_id]; break
                        
                        if img:
                            iw, ih = (int(zw), int(zh)) if layer == LAYER_BASE else (int(img.get_width()*self.zoom_level), int(img.get_height()*self.zoom_level))
                            img_s = pygame.transform.scale(img, (max(1, iw), max(1, ih)))
                            if cell.get(f"{layer}_rot", 0) != 0: img_s = pygame.transform.rotate(img_s, -cell[f"{layer}_rot"]); img_s = pygame.transform.scale(img_s, (max(1, iw), max(1, ih)))
                            if layer == LAYER_BASE: self.screen.blit(img_s, (sx - zw//2, sy))
                            else:
                                fw, fh = self.am.get_asset_footprint(item_id, cell.get(f"{layer}_rot", 0))
                                scx = (x - y) * (zw // 2) + self.camera_offset.x
                                scy = (x + y) * (zh // 2) + self.camera_offset.y
                                self.screen.blit(img_s, (scx - img_s.get_width()//2, scy + zh//2 - img_s.get_height()))

                    # Draw Coordinates (REQ-VIS-01) - only if zoom is close enough
                    if self.zoom_level > 1.2:
                        coord_txt = self.font.render(f"{x},{y}", True, (80, 80, 100))
                        self.screen.blit(coord_txt, (sx - coord_txt.get_width()//2, sy + zh//2 - coord_txt.get_height()//2))

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
            self.ui.draw_menu_bar(); self.ui.draw_dropdowns(); self.ui.draw_sidebar(); self.ui.draw_modal(); self.ui.draw_status_message(); pygame.display.flip(); self.clock.tick(60)

    def update_ui_layout(self):
        self.buttons = []
        menu_x = 10
        for menu in self.menu_items.keys():
            txt = self.font.render(menu, True, TEXT_COLOR)
            rect = pygame.Rect(menu_x, 0, txt.get_width() + 20, self.top_bar_height)
            self.buttons.append({"rect": rect, "text": menu, "type": "menu_root", "value": menu})
            menu_x += rect.width + 5
        
        tools_y = self.top_bar_height + 145
        tool_btn_w = (self.ui_panel_width - 30) // 2
        tools = [("UNDO [Z]", "undo"), ("REDO [Y]", "redo"), ("ROTATE [R]", "rotate"), ("SHADOW [G]", "shadow"), ("CLEAR [X]", "clear")]
        for i, (text, val) in enumerate(tools):
            bx = self.w - self.ui_panel_width + 10 + (i % 2) * (tool_btn_w + 10)
            by = tools_y + (i // 2) * 40
            self.buttons.append({"rect": pygame.Rect(bx, by, tool_btn_w, 30), "text": text, "type": "tool", "value": val})

        self.modal_rect = pygame.Rect(self.w//2 - 200, self.h//2 - 100, 400, 200)
        
    def show_confirmation(self, target):
        self.confirm_target = target
        self.modal_buttons = [
            {"rect": pygame.Rect(self.modal_rect.x + 50, self.modal_rect.y + 130, 120, 40), "text": "YES", "value": True},
            {"rect": pygame.Rect(self.modal_rect.x + 230, self.modal_rect.y + 130, 120, 40), "text": "NO", "value": False}
        ]

    def save_map(self):
        try:
            path = get_file_path(os.path.join(BASE_DIR, "maps"), "json", save=True)
            if not path: return
            with open(path, 'w') as f:
                json.dump({"version": VERSION, "grid": self.grid}, f)
            self.status_message = "MAP SAVED SUCCESSFULLY"
            self.status_timer = 180
        except Exception as e:
            self.status_message = f"ERROR SAVING MAP: {e}"
            self.status_timer = 180

    def load_map(self):
        try:
            path = get_file_path(os.path.join(BASE_DIR, "maps"), "json")
            if not path: return
            with open(path, 'r') as f:
                data = json.load(f)
                if data.get("version") != VERSION:
                    self.status_message = f"VERSION MISMATCH: {data.get('version')} vs {VERSION}"
                    self.status_timer = 180
                self.grid = data["grid"]
                self.undo_stack.clear(); self.redo_stack.clear()
            self.status_message = "MAP LOADED"
            self.status_timer = 120
        except Exception as e:
            self.status_message = f"ERROR LOADING MAP: {e}"
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
        elif val == "rotate": self.brush_rot = (self.brush_rot + 90) % 360
        elif val == "clear": self.brush_fh = self.brush_fv = self.brush_shadow = False; self.brush_rot = 0
        elif val == "grid": self.show_grid = not self.show_grid
        elif val == "sidebar": self.ui_panel_width = 250 if self.ui_panel_width == 0 else 0; self.update_ui_layout()
