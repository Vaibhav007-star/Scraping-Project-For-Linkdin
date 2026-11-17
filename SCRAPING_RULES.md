# Universal UI Scraping, Exploration & Screen Recording Specification

This specification defines the universal, battle-tested standard governing automated UI exploration, dynamic user simulation, and high-definition video recording across all 20+ Data Science, Machine Learning, and AI project showcases in this pipeline (supporting both Localhost servers and live Vercel/Cloud deployments).

---

## 1. Core Mission & Foundational Principles

### 1.1 Zero Artificial Time Limits
Every showcase video must be **unhurried, thorough, and exhaustive**. 
- There is **no arbitrary cap** (e.g., 15s or 30s).
- The recording length is determined strictly by the project's complexity: whether a project requires **60 seconds, 90 seconds, or 2.5 minutes** to showcase every single model and view, it is granted the full duration needed.

### 1.2 100% Feature Inventory Coverage
A project demonstration must never be a shallow skim:
- Every tab, navigation sub-view, model toggle, input slider, dropdown selector, visual canvas, and technical metric table must be visited and demonstrated **sequentially one by one**.

---

## 2. Mandatory Scraping & Exploration Protocols

### Protocol 1: Navigation Hierarchy & The "Zero Overview-Only" Rule
- **The Overview Trap Prohibition**: The recorder must **never** remain confined to the default `Overview` or Home landing screen.
- **Universal Multi-Tab Traversal**: When an application provides top-level navigation, every tab must be systematically clicked:
  - **Next.js / React Apps**: `button[data-tab]`, `.nav-links button`, `nav a`, `[role="tab"]`, `.tab-item`
  - **Streamlit Apps**: `.stTabs [data-baseweb="tab"]`, `.stTabs button`, `[data-testid="stSidebarNav"] li`
  - **Gradio Apps**: `button.tab-nav`, `.tabs button`
  - **FastAPI / Swagger UI**: `.opblock-tag-section`, `.opblock-summary`, `button.try-out__btn`
- **Demonstration Dwell**: Spend **3.0 to 4.5 seconds** per tab or sub-view to allow video viewers to read headings, inspect the layout, and absorb visual telemetry.

### Protocol 2: Multi-Action Dynamic Interaction Types
The pipeline supports five discrete, humanized interaction types defined in `projects_config.json`:

| Action Type | Parameters | Behavior & Visual Execution |
| :--- | :--- | :--- |
| **`click`** | `selector`, `wait_ms` | Pre-scrolls element into view, glides the animated cursor with Bézier curves, holds 300ms, and clicks with an animated green pulse. |
| **`slider`** | `selector`, `value`, `wait_ms` | Glides cursor to the range slider track, smoothly sets the target numeric value, and dispatches real `input` and `change` DOM events so reactive frameworks (React, Vue, Streamlit) immediately update. |
| **`select`** | `selector`, `value`, `wait_ms` | Moves pointer to the `<select>` or dropdown, picks the target option, and dispatches change events to trigger downstream model updates. |
| **`input` / `type`**| `selector`, `text`, `wait_ms` | Focuses the input element, clears previous text, and types character-by-character at a natural human typing cadence (45ms per keystroke). |
| **`scroll`** | `delta_y`, `wait_ms` | Executes multi-step, incremental mouse wheel scrolls (6 sub-steps, 180ms delay) to showcase vertical page depth without jarring page jumps. |
| **`hover`** | `selector`, `wait_ms` | Glides the cursor to highlight an essential visual badge, architecture node, or telemetry metric card. |

### Protocol 3: Real Model Inference & Visual Layer Cycling
Every AI capability on screen must be triggered live:
1. **Trigger Computation**: Click primary action buttons (`"Run U-Net Segmentation"`, `"Predict"`, `"Calculate"`, `"Simulate Greening"`, `"Generate Zones"`).
2. **Cycle Multi-Spectral / Multi-Class Layers**: If the UI offers visual layers (e.g., *Raw Image*, *Predicted Mask*, *Blended Overlay*, *Thermal Heatmap*), click through each layer sequentially so recruiters see the computer vision pipeline in action.
3. **Multi-Dimensional Views**: When 3D, WebGL, or isometric options exist, activate them (`"3D Digital Twin"`, `"Thermal Heat Dome"`, `"Isometric View"`).

### Protocol 4: In-Depth Scroll Tours per Sub-View
- For any tab or page with vertical content:
  - Scroll downward (`delta_y: 350..450`) to display lower metric charts, model architectures, and confusion matrices.
  - Pause scrolling for at least **3.5 seconds** when a chart or table is in the viewport.
  - Smoothly scroll back up to the navigation bar before transitioning to the next tab.

### Protocol 5: Visual Animated Cursor Simulation
- A high-contrast animated cursor (`#playwright-demo-cursor`) is injected into the DOM on page load:
  - **Neutral State**: 22px vibrant red pointer with a crisp white border and drop-shadow (`rgba(239, 68, 68, 0.85)`).
  - **Motion**: Interpolated multi-frame movements (8–12 frames) simulate genuine human mouse tracking.
  - **Click Pulse**: Scales dynamically to 1.6x and turns bright emerald green (`rgba(16, 185, 129, 0.95)`) on click, giving unmistakable visual cues to video viewers.

### Protocol 6: Heavy Canvas, WebGL & Plotly Rendering Buffers
- Deep learning visualizers, Mapbox tiles, Leaflet maps, and Three.js scenes require GPU / canvas stabilization.
- Always allocate a **3.0 to 4.0 second stabilization dwell** after switching to heavy WebGL or map views before moving the cursor or scrolling.

### Protocol 7: Destructive Selector Exclusion
- The automated recorder is strictly prohibited from clicking:
  - Action labels containing `"Delete"`, `"Drop"`, `"Sign Out"`, `"Log Out"`, `"Purge"`, `"Clear All"`.
  - External social links, third-party GitHub stars, or external URLs that take the browser away from the project deployment.

### Protocol 8: Universal Closing & Hero Wrap-Up
- Always end every demonstration by navigating back to the main **Overview / Hero** screen, letting the cursor rest naturally for 3.0 seconds. This creates a polished, professional loop for LinkedIn autoplay videos.

### Protocol 9: Video Post-Processing & Export Standard
- **Load Trimming**: Programmatically trims the initial **2.00 seconds** of blank loading / DNS resolution.
- **Dynamic Speed Optimization**: Applies a mild **1.15x to 1.20x** acceleration factor to keep the presentation snappy and engaging without rushing complex plots.
- **Universal Codec**: Rendered via MoviePy with H.264 video codec (`libx264`), `yuv420p` pixel format, and faststart metadata flags to ensure zero playback errors across LinkedIn web, iOS, and Android clients.

---

## 3. Standard Configuration Schema (`projects_config.json`)

To configure any new Data Science or AI project for the pipeline, use this standardized schema:

```json
{
  "name": "project_identifier",
  "title": "Full Formal Title of the AI Platform",
  "live_url": "https://your-project.vercel.app",
  "trim_start_sec": 2.0,
  "speed_factor": 1.18,
  "interactions": [
    { "action": "hover", "selector": "header, .brand", "wait_ms": 2500, "description": "1. Highlight Header & Problem Framing" },
    { "action": "click", "selector": "button[data-tab='tab_id']", "wait_ms": 3000, "description": "2. Navigate to Feature Tab" },
    { "action": "click", "selector": "button:has-text('Run Inference')", "wait_ms": 4000, "description": "3. Execute Neural Model" },
    { "action": "slider", "selector": "input[type='range']", "value": "45", "wait_ms": 3000, "description": "4. Adjust Interactive Parameter" },
    { "action": "scroll", "delta_y": 400, "wait_ms": 3500, "description": "5. Inspect Convergence Curves & Metrics" },
    { "action": "scroll", "delta_y": -400, "wait_ms": 1000, "description": "6. Return to Tab Header" },
    { "action": "click", "selector": "button[data-tab='overview']", "wait_ms": 3000, "description": "7. Conclude on Hero Overview" }
  ]
}
```

---

## 4. Automatic Discovery Fallback (When Custom Interactions are Omitted)

If a project in `projects_config.json` does not specify an explicit `interactions` array:
1. **Gemini Multimodal Vision Director** analyzes the initial screenshot and designs an initial visual exploration roadmap.
2. **Deep DOM Feature Explorer (`_explore_remaining_features`)** automatically:
   - Scans for all navigation tabs (`button[data-tab]`, `nav button`, `.stTabs [data-baseweb="tab"]`, `[role="tab"]`).
   - Clicks through each tab sequentially with 3.0s dwell.
   - Detects and triggers action buttons (`"Run"`, `"Predict"`, `"Simulate"`, `"Calculate"`).
   - Adjusts any visible sliders.
   - Performs a complete vertical page scroll through all charts, tables, and architectural diagrams.
   - Gracefully returns to the top hero section.

---

## 5. Quality Assurance Verification Checklist

Before publishing any project showcase to LinkedIn:
- [x] **All Tabs Visited**: No video is stuck on the overview page; every single tab option is opened and showcased.
- [x] **Models Executed**: All inference buttons are clicked and their visual output (masks, overlays, heatmaps, gauges) is clearly recorded.
- [x] **Interactive Reaction**: Sliders and dropdowns visibly alter parameters and trigger dynamic recalculation.
- [x] **Animated Pointer**: Cursor is clearly visible, moves smoothly, and pulses green on each click.
- [x] **Clean Loop**: The video starts after DNS load and concludes back on the clean overview dashboard.
- [x] **Standard Encoding**: 1080p or 720p H.264 `yuv420p` MP4 ready for LinkedIn upload.
