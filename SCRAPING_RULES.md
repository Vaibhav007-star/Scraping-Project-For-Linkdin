# Automated Feature Exploration & Screen Recording Specification

This specification defines the universal protocol and rules governing automated UI exploration, dynamic interaction, and screen recording across all Data Science, AI, and Machine Learning project showcases (both Localhost servers and live Vercel/Cloud deployments).

---

## 1. Core Mission
Every recording must serve as a **compelling, production-grade video demo** that proves the project works interactively. The recording engine must behave like an experienced practitioner giving a live product demo to an engineering recruiter or investor.

---

## 2. Mandatory Exploration Rules

### Rule 1: Complete Feature & View Coverage (Never Record a Static Page)
- **Zero Idle Footage**: Never stay static on the initial landing view for more than 2.5 seconds.
- **Systematic Tab Traversal**: Detect and visit every tab, sidebar link, or sub-view (`.stTabs`, `[role="tab"]`, `.tab-btn`, `nav a`) sequentially.
- **View Dwell Allocation**: Spend 2.5 to 4 seconds on each major view so viewers can absorb the UI context before moving to the next section.
- **Return to Hero**: Always return to the primary interactive dashboard before concluding the recording.

### Rule 2: Natural, Cinematic Scrolling Dynamics
- **Smooth Step Scrolling**: Absolutely no instant, jarring page jumps (`window.scrollTo(0, 9999)`).
- **Interpolated Wheel Movement**: Use incremental wheel actions (`mouse.wheel(0, 250..350)`) with realistic dwell intervals (600ms–1000ms) between scroll increments.
- **Chart & Table Inspection**: When reaching data visualizers (interactive plots, Leaflet/Mapbox maps, confusion matrices, loss curves, or SHAP graphs), pause scrolling for at least 2 seconds so the visualization can be clearly seen.
- **Bi-Directional Pan**: Scroll down to display the architecture, model pipeline, and lower metrics, then smoothly scroll back up to the top summary.

### Rule 3: Visual Mouse Cursor Simulation
- **Visible Pointer Overlay**: A high-contrast animated cursor must be injected directly into the DOM (`playwright-demo-cursor`).
- **Humanized Curved Trajectories**: The mouse must glide across screen coordinates in interpolated steps (minimum 8–10 interpolation frames per movement) rather than snapping instantaneously.
- **Click Feedback**: The pointer must visually pulse (scaling from 1.0x to 1.5x and transitioning color) on `mousedown`/`mouseup` to clearly signal user clicks to video viewers.

### Rule 4: Active Parameter & Form Manipulation
- **Interactive Control Touches**: Locate inputs, sliders, and dropdown menus (`<select>`, `input[type="number"]`, range sliders).
- **Parameter Mutation**: Modify at least one input parameter (e.g., contract tenure, risk threshold, sensitivity value) using arrow keys or select triggers.
- **Primary Action Trigger**: Identify and click the main execution button (`"Predict"`, `"Run Inference"`, `"Calculate"`, `"Generate"`, `"Simulate"`, `"Apply Mask"`).
- **Result Reaction**: Wait 1.5 to 3.0 seconds after triggering execution to record the resulting animation, prediction badge, or updated graph.

### Rule 5: Heavy Visual & Canvas Rendering Readiness
- **Map & Canvas Wait**: WebGL, Mapbox, Leaflet, and Three.js canvases must be allowed a minimum 2-second stabilization buffer after tab switching to finish vector tile rendering.
- **Chart Animation Buffer**: ApexCharts, Chart.js, and Plotly animations must be given sufficient time to complete their transition animations before mouse scrolling resumes.

### Rule 6: Destructive Action Exclusion
- **Blacklisted Selectors**: Never click elements with text matching `"Reset"`, `"Delete"`, `"Drop"`, `"Sign Out"`, `"Log Out"`, `"Cancel"`, or outbound external links that navigate away from the project domain.

### Rule 7: Timing, Speed, and Duration Guarantee
- **Raw Duration Target**: Capture a minimum of **40 to 45 seconds** of raw continuous interaction.
- **Post-Processing Target**:
  - Trim the first **2.0 seconds** of blank loading/DNS resolution.
  - Apply an acceleration factor of **1.18x to 1.25x** for energetic social media pacing.
  - **Guaranteed Final Video Duration**: **At least 30 to 40 seconds** of high-density feature demonstration.

---

## 3. Dual-Engine Architecture

```text
                               +----------------------------+
                               | 1. Launch URL / Vercel App |
                               +----------------------------+
                                             |
                                             v
                               +----------------------------+
                               | 2. Inject Visual Cursor    |
                               +----------------------------+
                                             |
                                             v
                      +----------------------------------------------+
                      |         Gemini Vision Director Mode          |
                      |  - Captures viewport screenshot (1280x720)   |
                      |  - Gemini analyzes UI layout & visual appeal |
                      |  - Generates 5-7 step strategic demo tour    |
                      +----------------------------------------------+
                                             |
                     [Vision Steps Available?]
                           /                   \
                        (Yes)                  (No / Timeout)
                         /                       \
                        v                         v
         +-----------------------------+   +-----------------------------+
         | Execute AI-Directed Tour    |   | Autonomous DOM Explorer     |
         | (Targeted coordinates,      |   | (Systematic tab traversal,  |
         |  feature toggles & hovers)  |   |  action buttons, inputs)    |
         +-----------------------------+   +-----------------------------+
                        \                         /
                         \                       /
                          v                     v
                      +----------------------------------+
                      | Complete 40s Deep Feature Tour   |
                      | - Full page visual scroll        |
                      | - Inspect all charts & metrics   |
                      | - Smooth return to hero banner   |
                      +----------------------------------+
                                        |
                                        v
                      +----------------------------------+
                      | MoviePy Video Editor             |
                      | - Trim initial 2.0s load screen  |
                      | - Apply 1.18x social speedup     |
                      | - Render H.264 MP4 (>= 30s)      |
                      +----------------------------------+
```

---

## 4. Project Configuration Example (`projects_config.json`)

To apply these rules to any project, simply define its entry:

```json
{
  "name": "urban_heat_islands",
  "title": "Urban Heat Island (UHI) AI Mitigation & Satellite Analysis Platform",
  "live_url": "https://urban-heat-islands.vercel.app",
  "record_duration_seconds": 40,
  "trim_start_sec": 2.0,
  "speed_factor": 1.18,
  "interactions": [
    { "action": "click", "selector": "button:has-text('Mask')", "wait_ms": 2500 },
    { "action": "click", "selector": "button:has-text('Overlay')", "wait_ms": 2500 },
    { "action": "scroll", "delta_y": 350, "wait_ms": 2000 },
    { "action": "click", "selector": "button:has-text('Isometric')", "wait_ms": 2000 }
  ]
}
```

---

## 5. Summary Checklist for Every Showcase Video
- [x] Initial blank screen trimmed out.
- [x] Visible animated mouse pointer showing actions.
- [x] Every main tab/view opened and demonstrated.
- [x] Action button clicked and resulting predictions showcased.
- [x] Smooth, readable scrolling across charts and maps.
- [x] Final video length strictly greater than or equal to 30 seconds.
- [x] Exported in LinkedIn-optimized format (H.264 codec, `yuv420p` pixel format).
