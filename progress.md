Original prompt: Not a fan of any of these options. would like a version where import containers flowing from top to bottom and export containers from bottom to top.
Top is berth spaces (horizontal). Vessels arrive from left. Leave from right. There's a button for adding a vessel or removing a vessel (number of containers in disrupting vessel is fixed and hidden).
We see the cranes used and not used linked to vessels or not with an implicity crane layer. Color code for when crane is used and when it's not. With possibility to add or remove cranes with one + and one - button.
Forklift layer with current number of forklifts operating. same logic of colors for activity and + - buttons.
Yard layer. Let's ignore different types of containers. Includes current capacity.
Same logic for gates etc...
Also, the live ops is continuous. No start or end. User can speed up or slow down time and reset, so everything is empty.
Do you get my point? Try new candidates

- Creating a second concept set in `concepts-v2/` instead of replacing the first one.
- New candidates will all share the same directional layout:
  - berth row at the top
  - imports flowing down
  - exports flowing up
  - live continuous simulation feel
  - visible +/- controls for vessels, cranes, forklifts, and gates

- Added `concepts-v2/stacked-flow.html`, `concepts-v2/activity-stack.html`, and `concepts-v2/dock-playfield.html` with shared behavior in `concepts-v2/live-ops.js`.
- Verified all three concepts visually with the Playwright client after installing local `playwright` and Chromium.
- Confirmed browser state wiring directly with Playwright evaluation:
  - `add-vessel` adds a hidden-load vessel into the berth track
  - crane decrement updates total cranes
  - speed selection updates the selected speed state
  - reset clears vessels, yard, and active flows to zero
- Headless `page.click(selector)` was flaky on some static `file://` concept buttons even though the DOM handlers are working; direct DOM-triggered clicks confirmed the controls are wired correctly.

- User selected Candidate C for further iteration.
- Reworked `concepts-v2/dock-playfield.html` and added `concepts-v2/dock-playfield.js` so Candidate C can diverge from the shared mock behavior.
- Candidate C now has:
  - inline `+/-` vessel controls in the berth layer like the other resource layers
  - compact recent-usage charts in berth, crane, forklift, yard, and gate headers
  - explicit vessel state changes: fast arrival -> fixed berth occupancy -> fast departure
  - explicit truck state changes at gates: fast approach -> stationary gate service -> fast handoff/departure
  - queue counts defined as over-capacity pressure, not generic activity
  - layer tinting based on utilization / pressure
- Verification:
  - `node --check concepts-v2/dock-playfield.js`
  - Playwright screenshot pass for updated Candidate C
  - direct Playwright state checks for `add-vessel`, `dec-gates`, speed changes, and `reset`
