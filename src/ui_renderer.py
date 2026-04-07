import pygame
import sys
from .constants import *
from .utils import world_to_screen, screen_to_world

class UIRenderer:
    def __init__(self, editor):
        self.editor = editor
        self.font = editor.font
        self.bold_font = editor.bold_font
        self.icons = {}
        self.load_ui_icons()

    def load_ui_icons(self):
        try:
            icon_path = os.path.join(BASE_DIR, "assets", "ui", "icons")
            warning_img = pygame.image.load(os.path.join(icon_path, "warning_icon.png")).convert_alpha()
            self.icons['warning'] = pygame.transform.scale(warning_img, (40, 40))
            self.icons['status_err'] = pygame.transform.scale(warning_img, (24, 24))
        except Exception as e:
            print(f"Error loading UI icons: {e}")

    def draw_brush_preview(self, mx, my):
        """Draws a semi-transparent blue footprint of the selected item at (mx, my)."""
        if not self.editor.selected_item or mx > self.editor.w - self.editor.ui_panel_width: return
        
        gx, gy = screen_to_world(mx, my, self.editor.zoom_level, self.editor.camera_offset)
        fw, fh = self.editor.am.get_asset_footprint(self.editor.selected_item, self.editor.brush_rot)
        
        # Center the footprint on the mouse cell
        sx, sy = gx - fw // 2, gy - fh // 2
        
        zw, zh = TILE_W * self.editor.zoom_level, TILE_H * self.editor.zoom_level
        
        # 1. Draw the "Blue Mesh" (Footprint Area)
        preview_surf = pygame.Surface((self.editor.w, self.editor.h), pygame.SRCALPHA)
        for ix in range(fw):
            for iy in range(fh):
                tx, ty = sx + ix, sy + iy
                if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                    psx, psy = world_to_screen(tx, ty, self.editor.zoom_level, self.editor.camera_offset)
                    # Draw a semi-transparent blue diamond
                    pts = [(psx, psy), (psx + zw//2, psy + zh//2), (psx, psy + zh), (psx - zw//2, psy + zh//2)]
                    pygame.draw.polygon(preview_surf, (100, 200, 255, 100), pts)
                    pygame.draw.polygon(preview_surf, (150, 220, 255, 180), pts, 2)
        
        self.editor.screen.blit(preview_surf, (0, 0))
        
        # 2. Draw Ghost Asset (Semi-transparent)
        img = None
        # Check animations
        if self.editor.selected_item in self.editor.am.animations:
            img = self.editor.am.animations[self.editor.selected_item][0]
        else:
            for layer in self.editor.am.assets:
                for cat in self.editor.am.assets[layer].values():
                    if self.editor.selected_item in cat: img = cat[self.editor.selected_item]; break
                if img: break
        
        if img:
            iw, ih = int(img.get_width() * self.editor.zoom_level), int(img.get_height() * self.editor.zoom_level)
            # Handle Rotation for Ghost
            ghost = pygame.transform.scale(img, (iw, ih))
            if self.editor.current_layer == LAYER_BASE:
                ghost = pygame.transform.scale(ghost, (int(zw), int(zh)))
            
            if self.editor.brush_rot != 0:
                ghost = pygame.transform.rotate(ghost, -self.editor.brush_rot)
            
            ghost.set_alpha(150)
            
            # Position for ghost (centered on the footprint or current cell)
            if self.editor.current_layer == LAYER_BASE:
                gsx, gsy = world_to_screen(gx, gy, self.editor.zoom_level, self.editor.camera_offset)
                self.editor.screen.blit(ghost, (gsx - zw//2, gsy))
            else:
                scx = (gx - gy) * (zw // 2) + self.editor.camera_offset.x
                # Sync with StillnessEditor's bottom vertex anchor
                anchor_y = (gx + (fw - fw//2) + gy + (fh - fh//2)) * (zh // 2) + self.editor.camera_offset.y
                
                # Render Brush Shadow Preview
                if self.editor.current_layer == LAYER_OBJECTS and self.editor.brush_shadow:
                    # Create shadow ghost
                    shadow_ghost = pygame.transform.rotate(pygame.transform.scale(img, (iw, ih)), -self.editor.brush_rot)
                    shadow_surf = pygame.Surface(shadow_ghost.get_size(), pygame.SRCALPHA)
                    shadow_surf.blit(shadow_ghost, (0, 0))
                    shadow_surf.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_MULT)
                    shadow_surf = pygame.transform.scale(shadow_surf, (shadow_surf.get_width(), int(shadow_surf.get_height() * 0.5)))
                    self.editor.screen.blit(shadow_surf, (scx - shadow_surf.get_width()//2, anchor_y - shadow_surf.get_height()))

                self.editor.screen.blit(ghost, (scx - ghost.get_width()//2, anchor_y - ghost.get_height()))

        # 3. Paste Preview (REQ-EFF-04)
        if self.editor.paste_mode and self.editor.clipboard:
            cw, ch = len(self.editor.clipboard), len(self.editor.clipboard[0])
            for i, row in enumerate(self.editor.clipboard):
                for j, cell in enumerate(row):
                    tx, ty = gx + i, gy + j
                    if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                        psx, psy = world_to_screen(tx, ty, self.editor.zoom_level, self.editor.camera_offset)
                        pygame.draw.polygon(self.editor.screen, (100, 255, 100, 80), [(psx, psy), (psx+zw//2, psy+zh//2), (psx, psy+zh), (psx-zw//2, psy+zh//2)], 1)

    def draw_menu_bar(self):
        pygame.draw.rect(self.editor.screen, (40, 40, 45), (0, 0, self.editor.w, self.editor.top_bar_height))
        pygame.draw.line(self.editor.screen, (20, 20, 25), (0, self.editor.top_bar_height), (self.editor.w, self.editor.top_bar_height), 1)
        
        for b in self.editor.buttons:
            if b["type"] == "menu_root":
                is_active = (self.editor.active_menu == b["value"])
                if is_active: pygame.draw.rect(self.editor.screen, (60, 60, 70), b["rect"])
                txt = self.font.render(b["text"], True, TEXT_COLOR if not is_active else (255, 255, 255))
                self.editor.screen.blit(txt, (b["rect"].x + 10, (self.editor.top_bar_height - txt.get_height()) // 2))

    def draw_dropdowns(self):
        if not self.editor.active_menu: return
        items = self.editor.menu_items[self.editor.active_menu]
        m_rect = next(b["rect"] for b in self.editor.buttons if b["value"] == self.editor.active_menu)
        drop_w = 180
        pygame.draw.rect(self.editor.screen, (45, 45, 50), (m_rect.x, self.editor.top_bar_height, drop_w, len(items)*25))
        pygame.draw.rect(self.editor.screen, (100, 100, 110), (m_rect.x, self.editor.top_bar_height, drop_w, len(items)*25), 1)
        for i, (text, val) in enumerate(items):
            iy = self.editor.top_bar_height + i * 25
            if text == "-":
                pygame.draw.line(self.editor.screen, (100, 100, 110), (m_rect.x+5, iy+12), (m_rect.x+drop_w-5, iy+12))
            else:
                sub_r = pygame.Rect(m_rect.x, iy, drop_w, 25)
                if sub_r.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(self.editor.screen, (60, 100, 180), sub_r)
                txt = self.font.render(text, True, TEXT_COLOR)
                self.editor.screen.blit(txt, (m_rect.x + 10, iy + (25 - txt.get_height()) // 2))

    def draw_sidebar(self):
        if self.editor.ui_panel_width <= 0: return
        panel_x = self.editor.w - self.editor.ui_panel_width
        pygame.draw.rect(self.editor.screen, (35, 35, 40), (panel_x, self.editor.top_bar_height, self.editor.ui_panel_width, self.editor.h - self.editor.top_bar_height))
        pygame.draw.line(self.editor.screen, (60, 60, 70), (panel_x, self.editor.top_bar_height), (panel_x, self.editor.h), 1)
        
        y = self.editor.top_bar_height + 15
        info = [
            (f"LAYER: {self.editor.current_layer.upper()}", ACCENT_COLOR),
            (f"SELECTED: {self.editor.selected_item}", TEXT_COLOR),
            (f"ZOOM: {self.editor.zoom_level:.1f}x", TEXT_COLOR),
            (f"ROTATION: {self.editor.brush_rot}º", TEXT_COLOR),
            (f"GRID: {'ON' if self.editor.show_grid else 'OFF'}", (150, 150, 150)),
            (f"FOG: {'ON' if self.editor.show_fog else 'OFF'}", self.editor.fog_presets[self.editor.fog_color_idx]),
            (f"RAIN: {'ON' if self.editor.show_rain else 'OFF'}", (150, 160, 255) if self.editor.show_rain else (150, 150, 150))
        ]
        for text, color in info:
            txt = self.bold_font.render(text, True, color)
            self.editor.screen.blit(txt, (panel_x + 15, y))
            y += 25

        # Search Bar (REQ-EFF-03)
        y += 10
        search_rect = pygame.Rect(panel_x + 15, y, self.editor.ui_panel_width - 30, 30)
        pygame.draw.rect(self.editor.screen, (25, 25, 30), search_rect)
        
        # Highlight border if active
        border_color = (150, 200, 255) if self.editor.search_active else (60, 60, 70)
        if self.editor.search_query: border_color = ACCENT_COLOR
        pygame.draw.rect(self.editor.screen, border_color, search_rect, 1 if not self.editor.search_active else 2)
        
        search_text = f"Search: {self.editor.search_query}" if self.editor.search_query else "Search (Type...)"
        search_color = TEXT_COLOR if self.editor.search_query or self.editor.search_active else (100, 100, 100)
        stxt = self.font.render(search_text, True, search_color)
        self.editor.screen.blit(stxt, (search_rect.x + 10, search_rect.y + (30 - stxt.get_height()) // 2))
        
        # Blinking Cursor
        if self.editor.search_active and (pygame.time.get_ticks() // 500) % 2:
            cursor_x = search_rect.x + 10 + stxt.get_width() + 2
            pygame.draw.line(self.editor.screen, (255, 255, 255), (cursor_x, search_rect.y + 5), (cursor_x, search_rect.y + 25), 1)
        
        y += 40

        # Palette Clipping & Rendering
        palette_y_start = self.editor.top_bar_height + 360
        palette_rect = pygame.Rect(panel_x, palette_y_start, self.editor.ui_panel_width, self.editor.h - palette_y_start)
        
        # Set clip to prevent bleeding into other UI elements
        old_clip = self.editor.screen.get_clip()
        self.editor.screen.set_clip(palette_rect)
        
        ticks = pygame.time.get_ticks()
        for b in self.editor.palette_buttons:
            # Shift rect by scroll amount
            draw_rect = b["rect"].move(0, -self.editor.palette_scroll_y)
            if not palette_rect.colliderect(draw_rect): continue # Skip if off-screen
            
            pygame.draw.rect(self.editor.screen, (50, 50, 60), draw_rect)
            
            img = b.get("img")
            if b.get("anim") and b["name"] in self.editor.am.animations:
                frames = self.editor.am.animations[b["name"]]
                img = frames[(ticks // (1000 // ANIM_FPS)) % len(frames)]

            if img:
                thumb = pygame.transform.scale(img, (draw_rect.width-10, draw_rect.height-10))
                self.editor.screen.blit(thumb, (draw_rect.x+5, draw_rect.y+5))
            else:
                txt = self.font.render(b["name"].upper(), True, (150, 150, 150))
                self.editor.screen.blit(txt, (draw_rect.centerx - txt.get_width()//2, draw_rect.centery - txt.get_height()//2))
            
            if b.get("name") == self.editor.selected_item or b.get("name") == self.editor.current_cat:
                pygame.draw.rect(self.editor.screen, ACCENT_COLOR, draw_rect, 2)
            
            if b.get("anim"):
                pygame.draw.circle(self.editor.screen, (255, 100, 100), (draw_rect.right - 10, draw_rect.top + 10), 4)

        # Restore clip
        self.editor.screen.set_clip(old_clip)

        # Draw Scrollbar Indicator
        if self.editor.max_palette_scroll > 0:
            sb_h = max(20, (palette_rect.height / (palette_rect.height + self.editor.max_palette_scroll)) * palette_rect.height)
            sb_y = palette_y_start + (self.editor.palette_scroll_y / self.editor.max_palette_scroll) * (palette_rect.height - sb_h)
            sb_rect = pygame.Rect(self.editor.w - 6, sb_y, 4, sb_h)
            pygame.draw.rect(self.editor.screen, (100, 100, 110), sb_rect, border_radius=2)
        
        # Tools
        for b in self.editor.buttons:
            if b["type"] in ["tool", "toggle"]:
                active = False
                if b["value"] == "grid": active = self.editor.show_grid
                elif b["value"] == "shadow": active = self.editor.brush_shadow
                
                pygame.draw.rect(self.editor.screen, (60, 60, 70) if not active else (80, 120, 200), b["rect"])
                txt = self.font.render(b["text"], True, TEXT_COLOR)
                self.editor.screen.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))

        # Metadata Section (REQ-DATA-01)
        if self.editor.selection_start == self.editor.selection_end and self.editor.selection_start:
            gx, gy = self.editor.selection_start
            y = self.editor.top_bar_height + 270
            self.editor.screen.blit(self.bold_font.render("METADATA:", True, ACCENT_COLOR), (panel_x + 15, y))
            meta_rect = pygame.Rect(panel_x + 15, y + 25, self.editor.ui_panel_width - 30, 25)
            pygame.draw.rect(self.editor.screen, (20, 20, 25), meta_rect)
            
            border_col = (200, 200, 255) if self.editor.metadata_focus else (60, 60, 70)
            pygame.draw.rect(self.editor.screen, border_col, meta_rect, 1 if not self.editor.metadata_focus else 2)
            
            val = self.editor.grid[gx][gy].get("metadata", "")
            mtxt = self.font.render(val if val else "None...", True, (255, 255, 255) if val else (100, 100, 100))
            self.editor.screen.blit(mtxt, (meta_rect.x + 8, meta_rect.y + (25 - mtxt.get_height()) // 2))
            
            if self.editor.metadata_focus and (pygame.time.get_ticks() // 500) % 2:
                pygame.draw.line(self.editor.screen, (255, 255, 255), (meta_rect.x + 8 + mtxt.get_width() + 2, meta_rect.y + 5), (meta_rect.x + 8 + mtxt.get_width() + 2, meta_rect.y + 20), 1)

    def draw_modal(self):
        if not self.editor.confirm_target: return
        s = pygame.Surface((self.editor.w, self.editor.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.editor.screen.blit(s, (0, 0))
        
        pygame.draw.rect(self.editor.screen, (45, 45, 50), self.editor.modal_rect)
        pygame.draw.rect(self.editor.screen, ACCENT_COLOR, self.editor.modal_rect, 2)
        
        # Draw Warning Icon
        if 'warning' in self.icons:
            icon_rect = self.icons['warning'].get_rect(centerx=self.editor.modal_rect.centerx, y=self.editor.modal_rect.y + 20)
            self.editor.screen.blit(self.icons['warning'], icon_rect)

        msg = f"ARE YOU SURE YOU WANT TO {self.editor.confirm_target.upper()}?"
        txt = self.bold_font.render(msg, True, (255, 255, 255))
        self.editor.screen.blit(txt, (self.editor.modal_rect.centerx - txt.get_width()//2, self.editor.modal_rect.y + 70))
        
        for b in self.editor.modal_buttons:
            txt = self.font.render(b["text"], True, (255, 255, 255))
            self.editor.screen.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))

    def draw_weather_dialog(self):
        if not self.editor.show_weather_config: return
        s = pygame.Surface((self.editor.w, self.editor.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200)) # Darker overlay
        self.editor.screen.blit(s, (0, 0))
        
        r = self.editor.weather_rect
        pygame.draw.rect(self.editor.screen, (40, 40, 45), r)
        pygame.draw.rect(self.editor.screen, ACCENT_COLOR, r, 2)
        
        title = self.bold_font.render("WEATHER CONFIGURATION", True, ACCENT_COLOR)
        self.editor.screen.blit(title, (r.centerx - title.get_width()//2, r.y + 20))
        
        for b in self.editor.weather_buttons:
            # Determine state
            state_text = ""
            state_color = TEXT_COLOR
            val = b["value"]
            if val == "fog": 
                state_text = "[ ON ]" if self.editor.show_fog else "[ OFF ]"
                state_color = self.editor.fog_presets[self.editor.fog_color_idx] if self.editor.show_fog else (100, 100, 100)
            elif val == "fog_cycle": 
                state_text = f"Preset {self.editor.fog_color_idx + 1}"
            elif val == "rain": 
                state_text = "[ ON ]" if self.editor.show_rain else "[ OFF ]"
            elif val == "rain_density": 
                state_text = str(self.editor.rain_density)
            elif val == "rain_floor": 
                state_text = "[ YES ]" if self.editor.rain_collision_floor else "[ NO ]"
            elif val == "rain_obj": 
                state_text = "[ YES ]" if self.editor.rain_collision_objects else "[ NO ]"
            elif val == "rain_splash": 
                state_text = "[ YES ]" if self.editor.rain_splashes else "[ NO ]"
            elif val == "rain_angle":
                # Special drawing for slider
                bar_r = pygame.Rect(b["rect"].x + 130, b["rect"].y + 10, 60, 10)
                pygame.draw.rect(self.editor.screen, (30, 30, 35), bar_r)
                # Map angle (-10 to 10) to bar
                handle_x = bar_r.x + (self.editor.rain_angle + 10) / 20 * bar_r.width
                pygame.draw.circle(self.editor.screen, ACCENT_COLOR, (int(handle_x), bar_r.centery), 6)
                state_text = f"{self.editor.rain_angle}"
            
            # Hover effect
            is_hover = b["rect"].collidepoint(pygame.mouse.get_pos())
            bg_color = (60, 60, 70) if not is_hover else (80, 80, 90)
            if val == "close": bg_color = (120, 60, 60) if not is_hover else (150, 80, 80)
            
            pygame.draw.rect(self.editor.screen, bg_color, b["rect"])
            
            # Text
            txt = self.font.render(b["text"], True, (255, 255, 255))
            self.editor.screen.blit(txt, (b["rect"].x + 10, b["rect"].centery - txt.get_height()//2))
            
            if state_text:
                stxt = self.bold_font.render(state_text, True, state_color)
                self.editor.screen.blit(stxt, (b["rect"].right - stxt.get_width() - 10, b["rect"].centery - stxt.get_height()//2))

    def show_splash(self):
        splash_font = pygame.font.SysFont("Arial", 72, bold=True)
        sub_font = pygame.font.SysFont("Arial", 28)
        start_time = pygame.time.get_ticks()
        duration = 2000
        
        running_splash = True
        while running_splash:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type in [pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN]: running_splash = False
            
            elapsed = pygame.time.get_ticks() - start_time
            if elapsed > duration: running_splash = False
            
            self.editor.screen.fill(BG_COLOR)
            title = splash_font.render("STILLNESS POINT", True, (100, 255, 150))
            self.editor.screen.blit(title, (self.editor.w//2 - title.get_width()//2, self.editor.h//2 - 50))
            v_text = sub_font.render(f"WORLD EDITOR {VERSION}", True, (150, 150, 150))
            self.editor.screen.blit(v_text, (self.editor.w//2 - v_text.get_width()//2, self.editor.h//2 + 40))
            
            pygame.display.flip()
            self.editor.clock.tick(60)

    def draw_status_message(self):
        if not self.editor.status_message or self.editor.status_timer <= 0: return
        
        # Draw a semi-transparent bar at the bottom
        bar_h = 40
        s = pygame.Surface((self.editor.w, bar_h), pygame.SRCALPHA)
        is_error = "ERROR" in self.editor.status_message
        color = (200, 50, 50, 200) if is_error else (50, 180, 80, 200)
        s.fill(color)
        self.editor.screen.blit(s, (0, self.editor.h - bar_h))
        
        # Draw text + Icon
        txt = self.bold_font.render(self.editor.status_message.upper(), True, (255, 255, 255))
        text_x = self.editor.w//2 - txt.get_width()//2
        text_y = self.editor.h - bar_h + (bar_h - txt.get_height())//2
        
        if is_error and 'status_err' in self.icons:
            self.editor.screen.blit(self.icons['status_err'], (text_x - 30, text_y + (txt.get_height() - 24)//2))
            
        self.editor.screen.blit(txt, (text_x, text_y))
