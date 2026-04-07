import pygame
import sys
import os
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
            pass

    def draw_brush_preview(self, mx, my):
        """Draws a semi-transparent blue footprint of the selected item at (mx, my)."""
        if not self.editor.ui_rects["viewport"].collidepoint(mx, my): return
        if not self.editor.selected_item: return
        
        gx, gy = screen_to_world(mx, my, self.editor.zoom_level, self.editor.camera_offset)
        fw, fh = self.editor.am.get_asset_footprint(self.editor.selected_item, self.editor.brush_rot)
        
        sx, sy = gx - fw // 2, gy - fh // 2
        zw, zh = TILE_W * self.editor.zoom_level, TILE_H * self.editor.zoom_level
        
        # 1. Draw the "Blue Mesh" (Footprint Area)
        preview_surf = pygame.Surface((self.editor.w, self.editor.h), pygame.SRCALPHA)
        for ix in range(fw):
            for iy in range(fh):
                tx, ty = sx + ix, sy + iy
                if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
                    psx, psy = world_to_screen(tx, ty, self.editor.zoom_level, self.editor.camera_offset)
                    pts = [(psx, psy), (psx + zw//2, psy + zh//2), (psx, psy + zh), (psx - zw//2, psy + zh//2)]
                    pygame.draw.polygon(preview_surf, (100, 200, 255, 80), pts)
                    pygame.draw.polygon(preview_surf, (150, 220, 255, 150), pts, 1)
        
        self.editor.screen.blit(preview_surf, (0, 0))
        
        # 2. Ghost Asset
        img = None
        if self.editor.selected_item in self.editor.am.animations:
            img = self.editor.am.animations[self.editor.selected_item][0]
        else:
            for layer in self.editor.am.assets:
                for cat in self.editor.am.assets[layer].values():
                    if self.editor.selected_item in cat: img = cat[self.editor.selected_item]; break
                if img: break
        
        if img:
            iw, ih = int(img.get_width() * self.editor.zoom_level), int(img.get_height() * self.editor.zoom_level)
            ghost = pygame.transform.scale(img, (iw, ih))
            if self.editor.current_layer == LAYER_BASE:
                ghost = pygame.transform.scale(ghost, (int(zw), int(zh)))
            if self.editor.brush_rot != 0:
                ghost = pygame.transform.rotate(ghost, -self.editor.brush_rot)
            ghost.set_alpha(150)
            
            if self.editor.current_layer == LAYER_BASE:
                gsx, gsy = world_to_screen(gx, gy, self.editor.zoom_level, self.editor.camera_offset)
                self.editor.screen.blit(ghost, (gsx - zw//2, gsy))
            else:
                scx = (gx - gy) * (zw // 2) + self.editor.camera_offset.x
                anchor_y = (gx + (fw - fw//2) + gy + (fh - fh//2)) * (zh // 2) + self.editor.camera_offset.y
                self.editor.screen.blit(ghost, (scx - ghost.get_width()//2, anchor_y - ghost.get_height()))

    def draw_menu_bar(self):
        r = self.editor.ui_rects["top_bar"]
        pygame.draw.rect(self.editor.screen, (40, 40, 45), r)
        pygame.draw.line(self.editor.screen, (20, 20, 25), (0, UI_TOP_BAR_H), (self.editor.w, UI_TOP_BAR_H), 1)
        for b in self.editor.buttons:
            if b["type"] == "menu_root":
                is_active = (self.editor.active_menu == b["value"])
                if is_active: pygame.draw.rect(self.editor.screen, (60, 60, 70), b["rect"])
                txt = self.font.render(b["text"], True, TEXT_COLOR if not is_active else (255, 255, 255))
                self.editor.screen.blit(txt, (b["rect"].x + 10, (UI_TOP_BAR_H - txt.get_height()) // 2))

    def draw_left_toolbar(self):
        r = self.editor.ui_rects["left_toolbar"]
        pygame.draw.rect(self.editor.screen, (35, 35, 40), r)
        pygame.draw.line(self.editor.screen, (60, 60, 70), (UI_LEFT_TOOLBAR_W, UI_TOP_BAR_H), (UI_LEFT_TOOLBAR_W, self.editor.h - UI_BOTTOM_BAR_H), 1)
        
        mx, my = pygame.mouse.get_pos()
        hovered_caption = None
        hovered_rect = None

        for b in self.editor.buttons:
            if b["type"] == "tool":
                is_active = (self.editor.active_tool == b["value"])
                is_hover = b["rect"].collidepoint(mx, my)
                
                bg_col = (80, 120, 200) if is_active else (50, 50, 55)
                if is_hover: 
                    bg_col = (70, 70, 80) if not is_active else (100, 140, 220)
                    hovered_caption = b.get("caption")
                    hovered_rect = b["rect"]

                pygame.draw.rect(self.editor.screen, bg_col, b["rect"], border_radius=4)
                pygame.draw.rect(self.editor.screen, (100, 100, 110), b["rect"], 1, border_radius=4)
                
                txt_col = (255, 255, 255) if is_active else (180, 180, 180)
                txt = self.bold_font.render(b["text"], True, txt_col)
                self.editor.screen.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))

        # Render Tooltip (Overlay)
        if hovered_caption:
            tip_txt = self.font.render(hovered_caption, True, (255, 255, 255))
            tip_w, tip_h = tip_txt.get_width() + 16, tip_txt.get_height() + 8
            tip_rect = pygame.Rect(hovered_rect.right + 10, hovered_rect.centery - tip_h//2, tip_w, tip_h)
            
            # Simple Arrow (Triangle)
            pygame.draw.polygon(self.editor.screen, (40, 40, 45), [
                (tip_rect.left, tip_rect.centery), 
                (tip_rect.left - 6, tip_rect.centery - 6), 
                (tip_rect.left - 6, tip_rect.centery + 6)
            ])
            
            pygame.draw.rect(self.editor.screen, (40, 40, 45), tip_rect, border_radius=4)
            pygame.draw.rect(self.editor.screen, ACCENT_COLOR, tip_rect, 1, border_radius=4)
            self.editor.screen.blit(tip_txt, (tip_rect.x + 8, tip_rect.y + 4))


    def draw_right_sidebar(self):
        r = self.editor.ui_rects["right_sidebar"]
        pygame.draw.rect(self.editor.screen, (35, 35, 40), r)
        pygame.draw.line(self.editor.screen, (60, 60, 70), (r.x, UI_TOP_BAR_H), (r.x, self.editor.h - UI_BOTTOM_BAR_H), 1)
        for b in self.editor.buttons:
            if b["type"] == "tab":
                is_active = (self.editor.active_tab == b["value"])
                bg_col = (45, 45, 52) if is_active else (30, 30, 35)
                pygame.draw.rect(self.editor.screen, bg_col, b["rect"])
                if is_active: pygame.draw.line(self.editor.screen, ACCENT_COLOR, (b["rect"].x, b["rect"].bottom-2), (b["rect"].right, b["rect"].bottom-2), 3)
                else: pygame.draw.line(self.editor.screen, (60, 60, 70), (b["rect"].x, b["rect"].bottom-1), (b["rect"].right, b["rect"].bottom-1), 1)
                txt_col = (255, 255, 255) if is_active else (130, 130, 140)
                txt = self.font.render(b["text"], True, txt_col)
                self.editor.screen.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))

        content_rect = pygame.Rect(r.x + 10, r.y + UI_TAB_H + 10, r.width - 20, r.height - UI_TAB_H - 20)
        getattr(self, f"draw_tab_{self.editor.active_tab}")(content_rect)

    def draw_tab_assets(self, r):
        search_rect = pygame.Rect(r.x, r.y, r.width, 30)
        pygame.draw.rect(self.editor.screen, (25, 25, 30), search_rect)
        border_color = ACCENT_COLOR if self.editor.search_active or self.editor.search_query else (60, 60, 70)
        pygame.draw.rect(self.editor.screen, border_color, search_rect, 1)
        stxt_content = f"Search: {self.editor.search_query}" if self.editor.search_query else "Search..."
        stxt = self.font.render(stxt_content, True, (200, 200, 200) if self.editor.search_query else (100, 100, 100))
        self.editor.screen.blit(stxt, (search_rect.x + 10, search_rect.y + (30 - stxt.get_height()) // 2))
        if self.editor.search_active and (pygame.time.get_ticks() // 500) % 2:
            pygame.draw.line(self.editor.screen, (255, 255, 255), (search_rect.x + 10 + stxt.get_width() + 2, search_rect.y + 6), (search_rect.x + 10 + stxt.get_width() + 2, search_rect.y + 24), 1)

        palette_y = r.y + 45
        palette_rect = pygame.Rect(r.x, palette_y, r.width, r.height - 45)
        old_clip = self.editor.screen.get_clip()
        self.editor.screen.set_clip(palette_rect)
        ticks = pygame.time.get_ticks()
        for b in self.editor.palette_buttons:
            draw_rect = b["rect"].copy()
            draw_rect.y -= self.editor.palette_scroll_y
            if not palette_rect.colliderect(draw_rect): continue
            pygame.draw.rect(self.editor.screen, (50, 50, 60), draw_rect)
            img = b.get("img")
            if b.get("anim") and b["name"] in self.editor.am.animations:
                frames = self.editor.am.animations[b["name"]]
                img = frames[(ticks // (1000 // ANIM_FPS)) % len(frames)]
            if img:
                thumb = pygame.transform.scale(img, (draw_rect.width-8, draw_rect.height-8))
                self.editor.screen.blit(thumb, (draw_rect.x+4, draw_rect.y+4))
            else:
                txt = self.font.render(b["name"][:10].upper(), True, (150, 150, 150))
                self.editor.screen.blit(txt, (draw_rect.centerx - txt.get_width()//2, draw_rect.centery - txt.get_height()//2))
            if b.get("name") == self.editor.selected_item or b.get("name") == self.editor.current_cat:
                pygame.draw.rect(self.editor.screen, ACCENT_COLOR, draw_rect, 2)
        self.editor.screen.set_clip(old_clip)
        if self.editor.max_palette_scroll > 0:
            sb_h = max(20, (palette_rect.height / (palette_rect.height + self.editor.max_palette_scroll)) * palette_rect.height)
            sb_y = palette_rect.y + (self.editor.palette_scroll_y / self.editor.max_palette_scroll) * (palette_rect.height - sb_h)
            pygame.draw.rect(self.editor.screen, (60, 60, 70), (self.editor.w - 8, palette_rect.y, 4, palette_rect.height))
            pygame.draw.rect(self.editor.screen, (120, 120, 130), (self.editor.w - 8, sb_y, 4, sb_h), border_radius=2)

    def draw_tab_inspector(self, r):
        y = r.y
        if self.editor.selection_start:
            gx, gy = self.editor.selection_start
            cell = self.editor.grid[gx][gy]
            self.editor.screen.blit(self.bold_font.render(f"CELL: {gx}, {gy}", True, ACCENT_COLOR), (r.x, y)); y += 30
            self.editor.screen.blit(self.font.render(f"Base ID: {cell.get('base_id') or 'None'}", True, (200, 200, 200)), (r.x, y)); y+=20
            self.editor.screen.blit(self.font.render(f"Object ID: {cell.get('objects_id') or 'None'}", True, (200, 200, 200)), (r.x, y)); y+=30
            self.editor.screen.blit(self.bold_font.render("OFFSETS (Arrow Keys):", True, (150, 150, 150)), (r.x, y)); y+=25
            self.editor.screen.blit(self.font.render(f"X: {cell.get('offset_x', 0)}  Y: {cell.get('offset_y', 0)}", True, (255, 255, 255)), (r.x + 10, y)); y+=35
            self.editor.screen.blit(self.bold_font.render("METADATA:", True, ACCENT_COLOR), (r.x, y)); y += 25
            meta_rect = pygame.Rect(r.x, y, r.width, 28)
            pygame.draw.rect(self.editor.screen, (20, 20, 25), meta_rect)
            pygame.draw.rect(self.editor.screen, (200, 200, 255) if self.editor.metadata_focus else (60, 60, 70), meta_rect, 1)
            val = cell.get("metadata", "")
            mtxt = self.font.render(val if val else "No metadata...", True, (255, 255, 255) if val else (100, 100, 100))
            self.editor.screen.blit(mtxt, (meta_rect.x + 8, meta_rect.y + (28 - mtxt.get_height()) // 2))
            if self.editor.metadata_focus and (pygame.time.get_ticks() // 500) % 2:
                pygame.draw.line(self.editor.screen, (255, 255, 255), (meta_rect.x + 8 + mtxt.get_width() + 1, meta_rect.y + 6), (meta_rect.x + 8 + mtxt.get_width() + 1, meta_rect.y + 22), 1)
            y += 45

        if self.editor.selected_fog_idx != -1:
            fz = self.editor.fog_zones[self.editor.selected_fog_idx]
            self.editor.screen.blit(self.bold_font.render("FOG ZONE PROPERTIES:", True, (255, 100, 100)), (r.x, y)); y += 25
            props = [(f"SHAPE: {fz.get('shape','rect').upper()}", "toggle_shape"), (f"DENSITY: {fz.get('density', 0.5):.1f}", "adj_density"), (f"FEATHER: {fz.get('feather', 0.2):.2f}", "adj_feather"), ("DELETE ZONE", "delete_zone")]
            for text, val in props:
                btn_r = pygame.Rect(r.x, y, r.width, 24)
                pygame.draw.rect(self.editor.screen, (50, 50, 60), btn_r)
                if btn_r.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(self.editor.screen, (70, 70, 80), btn_r)
                pygame.draw.rect(self.editor.screen, (80, 80, 90), btn_r, 1)
                ptxt = self.font.render(text, True, (255, 255, 255))
                self.editor.screen.blit(ptxt, (btn_r.x + 8, btn_r.y + (24 - ptxt.get_height()) // 2)); y += 28

    def draw_tab_scene(self, r):
        y = r.y
        self.editor.screen.blit(self.bold_font.render("ACTIVE LAYER:", True, ACCENT_COLOR), (r.x, y)); y += 25
        layers = [LAYER_BASE, LAYER_OBJECTS, LAYER_VFX, LAYER_COLLISION, LAYER_ANIM]
        for l in layers:
            btn_r = pygame.Rect(r.x, y, r.width, 24)
            if self.editor.current_layer == l: pygame.draw.rect(self.editor.screen, (60, 90, 150), btn_r)
            else: pygame.draw.rect(self.editor.screen, (45, 45, 50), btn_r)
            pygame.draw.rect(self.editor.screen, (80, 80, 90), btn_r, 1)
            ltxt = self.font.render(l.upper(), True, (255, 255, 255) if self.editor.current_layer == l else (150, 150, 150))
            self.editor.screen.blit(ltxt, (btn_r.x + 8, btn_r.y + (24 - ltxt.get_height()) // 2)); y += 28
        y += 15
        self.editor.screen.blit(self.bold_font.render("ENVIRONMENT:", True, ACCENT_COLOR), (r.x, y)); y += 25
        toggles = [(f"GRID: {'[ ON ]' if self.editor.show_grid else '[ OFF ]'}", self.editor.show_grid), (f"FOG: {'[ ON ]' if self.editor.show_fog else '[ OFF ]'}", self.editor.show_fog), (f"RAIN: {'[ ON ]' if self.editor.show_rain else '[ OFF ]'}", self.editor.show_rain)]
        for text, active in toggles:
            btn_r = pygame.Rect(r.x, y, r.width, 24)
            pygame.draw.rect(self.editor.screen, (50, 50, 60), btn_r)
            if btn_r.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(self.editor.screen, (70, 70, 80), btn_r)
            self.editor.screen.blit(self.font.render(text, True, ACCENT_COLOR if active else (150, 150, 150)), (btn_r.x + 8, btn_r.y + (24 - 18) // 2)); y += 28
        if self.editor.show_fog:
            btn_r = pygame.Rect(r.x + 20, y, r.width - 20, 22)
            pygame.draw.rect(self.editor.screen, self.editor.fog_presets[self.editor.fog_color_idx], btn_r)
            self.editor.screen.blit(self.font.render(f"Fog Preset: {self.editor.fog_color_idx + 1}", True, (0, 0, 0)), (btn_r.x + 8, btn_r.y + (22 - 18) // 2)); y += 26

    def draw_bottom_bar(self):
        r = self.editor.ui_rects["bottom_bar"]
        pygame.draw.rect(self.editor.screen, (30, 30, 35), r)
        pygame.draw.line(self.editor.screen, (60, 60, 70), (0, r.y), (self.editor.w, r.y), 1)
        self.editor.screen.blit(self.bold_font.render(f"TOOL: {self.editor.active_tool.upper()}", True, ACCENT_COLOR), (15, r.y + (r.height - 18) // 2))
        gx, gy = screen_to_world(*pygame.mouse.get_pos(), self.editor.zoom_level, self.editor.camera_offset)
        self.editor.screen.blit(self.font.render(f"GRID: {int(gx)}, {int(gy)} | ZOOM: {self.editor.zoom_level:.1f}x", True, (150, 150, 150)), (180, r.y + (r.height - 18) // 2))
        v_txt = self.font.render(VERSION, True, (100, 100, 110))
        self.editor.screen.blit(v_txt, (self.editor.w - v_txt.get_width() - 15, r.y + (r.height - 18) // 2))

    def draw_dropdowns(self):
        if not self.editor.active_menu: return
        items = self.editor.menu_items[self.editor.active_menu]
        m_root = next((b["rect"] for b in self.editor.buttons if b["value"] == self.editor.active_menu), None)
        if not m_root: return
        drop_w = 180
        drop_r = pygame.Rect(m_root.x, UI_TOP_BAR_H, drop_w, len(items)*25)
        pygame.draw.rect(self.editor.screen, (45, 45, 50), drop_r)
        pygame.draw.rect(self.editor.screen, (100, 100, 110), drop_r, 1)
        for i, (text, val) in enumerate(items):
            iy = UI_TOP_BAR_H + i * 25
            sub_r = pygame.Rect(m_root.x, iy, drop_w, 25)
            if text == "-": pygame.draw.line(self.editor.screen, (100, 100, 110), (sub_r.x+5, iy+12), (sub_r.right-5, iy+12))
            else:
                if sub_r.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(self.editor.screen, (60, 100, 180), sub_r)
                self.editor.screen.blit(self.font.render(text, True, TEXT_COLOR), (sub_r.x + 10, iy + (25 - 18) // 2))

    def draw_modal(self):
        if not self.editor.confirm_target: return
        s = pygame.Surface((self.editor.w, self.editor.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180)); self.editor.screen.blit(s, (0, 0))
        pygame.draw.rect(self.editor.screen, (45, 45, 50), self.editor.modal_rect)
        pygame.draw.rect(self.editor.screen, ACCENT_COLOR, self.editor.modal_rect, 2)
        txt = self.bold_font.render(f"ARE YOU SURE YOU WANT TO {self.editor.confirm_target.upper()}?", True, (255, 255, 255))
        self.editor.screen.blit(txt, (self.editor.modal_rect.centerx - txt.get_width()//2, self.editor.modal_rect.y + 60))
        for b in self.editor.modal_buttons:
            pygame.draw.rect(self.editor.screen, (80, 80, 90) if b["rect"].collidepoint(pygame.mouse.get_pos()) else (60, 60, 70), b["rect"])
            pygame.draw.rect(self.editor.screen, (150, 150, 160), b["rect"], 1)
            mtxt = self.font.render(b["text"], True, (255, 255, 255))
            self.editor.screen.blit(mtxt, (b["rect"].centerx - mtxt.get_width()//2, b["rect"].centery - mtxt.get_height()//2))

    def draw_status_message(self):
        if not self.editor.status_message or self.editor.status_timer <= 0: return
        bar_h = 40
        s = pygame.Surface((self.editor.w, bar_h), pygame.SRCALPHA)
        s.fill((200, 50, 50, 200) if "ERROR" in self.editor.status_message else (50, 180, 80, 200))
        self.editor.screen.blit(s, (0, self.editor.h - UI_BOTTOM_BAR_H - bar_h))
        txt = self.bold_font.render(self.editor.status_message.upper(), True, (255, 255, 255))
        self.editor.screen.blit(txt, (self.editor.w//2 - txt.get_width()//2, self.editor.h - UI_BOTTOM_BAR_H - bar_h + (bar_h - txt.get_height())//2))

    def show_splash(self):
        splash_font = pygame.font.SysFont("Arial", 64, bold=True)
        sub_font = pygame.font.SysFont("Arial", 24)
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < 1500:
            for event in pygame.event.get():
                if event.type in [pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]: return
            self.editor.screen.fill(BG_COLOR)
            t = splash_font.render("STILLNESS POINT", True, ACCENT_COLOR)
            v = sub_font.render(f"WORLD EDITOR {VERSION}", True, (150, 150, 150))
            self.editor.screen.blit(t, (self.editor.w//2 - t.get_width()//2, self.editor.h//2 - 40))
            self.editor.screen.blit(v, (self.editor.w//2 - v.get_width()//2, self.editor.h//2 + 30))
            pygame.display.flip(); self.editor.clock.tick(60)
