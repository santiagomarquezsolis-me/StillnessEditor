# Stillness Editor - Technical Requirements & Roadmap

This document serves as the professional blueprint for the **Stillness Editor**. It provides full traceability between features, implementation status, and verification tests.

## 📊 Requirements Status Matrix

| ID | Category | Requirement | Status | Verification / Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-CORE-01** | Core | Isometric Grid Rendering & Coordinate System | **DONE** | `test_coordinate_projection` |
| **REQ-CORE-02** | Core | Basic Asset Loading (Tiles/Objects/VFX) | **DONE** | `test_asset_footprint_logic` |
| **REQ-CORE-03** | Core | Map Persistence (JSON Save/Load) | **DONE** | `test_save_map_logic` |
| **REQ-CORE-04** | Core | Version-Locked File Handling | **DONE** | `test_map_version_lock` |
| **REQ-CORE-05** | Core | Robust Loading (Corrupted JSON Handling) | **DONE** | `test_map_corruption_handling` |
| **REQ-UI-01** | UI | High-Res Sidebar & Menu Bar Layout | **DONE** | `test_ui_distribution` |
| **REQ-UI-02** | UI | Professional Modals (Confirmations) | **DONE** | Manual (Visual Modals) |
| **REQ-CONF-01** | Config | Multi-Path Resource Configuration Dialog | **DONE** | Manual (Tkinter Dialog) |
| **REQ-CONF-02** | Config | UI Iconography (Folders, Warnings, Save) | **DONE** | Manual (Assets/UI/Icons) |
| **REQ-EFF-01** | Efficiency | Undo / Redo System (50-step stack) | PENDING | `test_undo_redo` |
| **REQ-EFF-02** | Efficiency | Fill / Bucket Tool (Adjacency check) | PENDING | `test_bucket_fill` |
| **REQ-EFF-03** | Efficiency | Asset Search & Tagging | PENDING | `test_palette_filter` |
| **REQ-ANIM-01** | Animation | Frame Sequence Detection (Auto-folder load) | PENDING | `test_anim_detection` |
| **REQ-ANIM-02** | Animation | Real-time Animation Preview (Sidebar Tool) | PENDING | Manual (UI Preview) |
| **REQ-ANIM-03** | Animation | Dynamic Stage Placement (Characters/VFX) | PENDING | `test_map_anim_data` |
| **REQ-SYS-01** | System | 90-Degree Map Camera Rotation | PENDING | `test_world_rotation` |
| **REQ-SYS-02** | System | Dynamic Map Resizing | PENDING | `test_grid_resize` |
| **REQ-ADV-01** | Engine | Auto-Tiling Rules (Bitmasking) | PENDING | `test_autotile_logic` |
| **REQ-PIPE-01** | Pipeline | Git Diff Visualizer (Map Versioning) | PENDING | Manual (Visual Diff) |

---

## 🟢 Level 1: Core & Configuration (Completed)
*Focus: Establishing the technical foundation and basic editor workflow.*

- **REQ-CORE-01**: Stable isometric projection (X+Y-Z) and grid management.
- **REQ-CORE-03**: Full map saving/loading with directory selection.
- **REQ-CONF-01**: Multi-path dialog (Config) to separate Tiles, Rocks, Structures and VFX.
- **REQ-CONF-02**: Premium visual feedback with icons for critical actions.

---

## 🟡 Level 2: High-Efficiency Workflow (Priority: HIGH)
*Focus: Speeding up map creation for high-scale production.*

1. **[REQ-EFF-01] Undo / Redo**: Command pattern implementation for non-destructive editing.
2. **[REQ-EFF-02] Bucket Fill**: Optimize large terrain areas with one click.
3. **[REQ-EFF-03] Selective Search**: Finding assets by keyword in the sidebar.
4. **[REQ-ANIM-01] Frame Detection**: Automatic recognition of `frame_XXX.png` sequences for batch loading.

---

## 🟠 Level 3: Dynamic Elements & Playback (Priority: MEDIUM)
*Focus: Adding life to the static isometric scenario.*

5. **[REQ-ANIM-02] Animation Preview Tool**: A specialized panel to pre-calculate and view frame playback before painting.
6. **[REQ-ANIM-03] Character & Effect Placement**: Support for animated objects on the grid (Looping vs. Triggered).
7. **[REQ-SYS-02] Grid Expansion**: Resizing maps to accommodate story growth.
8. **[REQ-CORE-06] Layer Grouping**: Folders for complex maps (e.g., "Forest Floor", "Canopy").

---

## 🔴 Level 4: Advanced Engine Integration (Priority: LOW)
*Focus: Real-time visual parity and complex spatial logic.*

9. **[REQ-SYS-01] Camera Rotation**: Full 90º world rotation (includes depth sorting update).
10. **[REQ-ADV-01] Auto-Tiling**: Implementing neighbor-aware terrain transitions.
11. **[REQ-ANIM-04] Particle Preview**: Real-time integration of game engine particle emitters (Smoke, Fire, Dust).
12. **[REQ-SYS-03] Trigger Logic Nodes**: Defining events and areas for gameplay scripting.

---

## 💎 Level 5: Professional Pipeline (Priority: FUTURE)
*Focus: Team collaboration and large-scale project management.*

13. **[REQ-PIPE-01] Version Control UI**: Visual diff between map versions based on Git commits.
14. **[REQ-PIPE-02] Plugin API**: Allowing external Python scripts to extend the editor tools.
15. **[REQ-PIPE-03] Asset Hot-Reloading**: Instant update when an external .png is saved.

---
*Last Updated: April 2026 - Santiago Marquez Solis*
