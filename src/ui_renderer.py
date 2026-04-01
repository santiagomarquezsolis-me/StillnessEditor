import pygame
import sys
from .constants import *

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
        panel_x = self.editor.w - self.editor.ui_panel_width
        pygame.draw.rect(self.editor.screen, (35, 35, 40), (panel_x, self.editor.top_bar_height, self.editor.ui_panel_width, self.editor.h - self.editor.top_bar_height))
        pygame.draw.line(self.editor.screen, (60, 60, 70), (panel_x, self.editor.top_bar_height), (panel_x, self.editor.h), 1)
        
        y = self.editor.top_bar_height + 15
        info = [
            (f"LAYER: {self.editor.current_layer.upper()}", (100, 200, 255)),
            (f"SELECTED: {self.editor.selected_item}", TEXT_COLOR),
            (f"ZOOM: {self.editor.zoom_level:.1f}x", TEXT_COLOR),
            (f"ROTATION: {self.editor.brush_rot}º", TEXT_COLOR),
            (f"GRID: {'ON' if self.editor.show_grid else 'OFF'}", (150, 150, 150))
        ]
        for text, color in info:
            txt = self.bold_font.render(text, True, color)
            self.editor.screen.blit(txt, (panel_x + 15, y))
            y += 25

        # Palette
        for b in self.editor.palette_buttons:
            pygame.draw.rect(self.editor.screen, (50, 50, 60), b["rect"])
            if b.get("img"):
                thumb = pygame.transform.scale(b["img"], (b["rect"].width-10, b["rect"].height-10))
                self.editor.screen.blit(thumb, (b["rect"].x+5, b["rect"].y+5))
            else:
                txt = self.font.render(b["name"].upper(), True, (150, 150, 150))
                self.editor.screen.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))
            
            if b.get("name") == self.editor.selected_item or b.get("name") == self.editor.current_cat:
                pygame.draw.rect(self.editor.screen, (100, 200, 255), b["rect"], 2)
        
        # Tools
        for b in self.editor.buttons:
            if b["type"] in ["tool", "toggle"]:
                active = False
                if b["value"] == "grid": active = self.editor.show_grid
                elif b["value"] == "shadow": active = self.editor.brush_shadow
                
                pygame.draw.rect(self.editor.screen, (60, 60, 70) if not active else (80, 120, 200), b["rect"])
                txt = self.font.render(b["text"], True, TEXT_COLOR)
                self.editor.screen.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))

    def draw_modal(self):
        if not self.editor.confirm_target: return
        s = pygame.Surface((self.editor.w, self.editor.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.editor.screen.blit(s, (0, 0))
        
        pygame.draw.rect(self.editor.screen, (45, 45, 50), self.editor.modal_rect)
        pygame.draw.rect(self.editor.screen, (100, 200, 255), self.editor.modal_rect, 2)
        
        # Draw Warning Icon
        if 'warning' in self.icons:
            icon_rect = self.icons['warning'].get_rect(centerx=self.editor.modal_rect.centerx, y=self.editor.modal_rect.y + 20)
            self.editor.screen.blit(self.icons['warning'], icon_rect)

        msg = f"ARE YOU SURE YOU WANT TO {self.editor.confirm_target.upper()}?"
        txt = self.bold_font.render(msg, True, (255, 255, 255))
        self.editor.screen.blit(txt, (self.editor.modal_rect.centerx - txt.get_width()//2, self.editor.modal_rect.y + 70))
        
        for b in self.editor.modal_buttons:
            pygame.draw.rect(self.editor.screen, (60, 60, 70), b["rect"])
            txt = self.font.render(b["text"], True, (255, 255, 255))
            self.editor.screen.blit(txt, (b["rect"].centerx - txt.get_width()//2, b["rect"].centery - txt.get_height()//2))

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
