# Playback Decisions

## Why The Playback View Exists

The static KPI dashboard explains what happened, but not always why it happened. The playback workspace was added so a user can connect operational events to queue growth, yard congestion, train departures, and vessel delay with less mental reconstruction.

The goal is not visual novelty. The goal is faster causal understanding.

## Core Product Decision

The playback view is a replay of a completed run, not a real-time simulation rendered in the browser.

This decision was made for four reasons:

1. It keeps playback deterministic. Scrubbing to the same timestamp always shows the same state.
2. It keeps the browser simple. The frontend does not need to rerun scheduling logic.
3. It makes synchronization easy. The same playback clock can drive map state, charts, bookmarks, and event cards.
4. It lets us support pause, resume, seek, and jump-to-event without simulation drift.

## Data Contract

The simulation engine now emits a playback bundle alongside the existing summary outputs.

The bundle contains:

- `snapshots`: a compact state capture every 15 simulated minutes
- `events`: high-signal operational bookmarks
- `duration_hours`
- `snapshot_interval_minutes`

The frontend uses this saved playback bundle directly. It does not reconstruct state from container rows.

## Why Snapshots Instead Of Per-Frame Rendering

The simulation already runs minute by minute on the backend. Rendering every minute of every entity would be excessive for the MVP and would produce too much client-side work.

Instead:

- snapshots provide stable state checkpoints
- lightweight interpolation from the current playback clock creates motion cues
- event bookmarks provide the narrative layer

This gives a useful replay without needing a heavy graphics pipeline.

## Why SVG For The First Version

The first playback view uses SVG and React instead of Pixi/WebGL.

That choice is deliberate:

- current flow density is moderate
- the animated objects are schematic, not photographic
- SVG is easier to inspect, style, and maintain in the current repo
- no additional rendering dependency was needed

If the product later needs thousands of simultaneous moving tokens, richer spatial routing, or more detailed animation layers, the map renderer should move to `PixiJS` while keeping the same playback data contract.

## Visual Design Rules

The playback map is schematic rather than literal:

- left: anchorage and quay
- center: yard blocks
- right: gate and rail
- moving tokens show flow direction and relative activity
- queue badges and utilization cues show pressure

The view intentionally focuses on shared-resource contention, not per-container micro-animation.

## Synchronization Model

Everything in the playback workspace is driven by a single shared playback clock:

- terminal map
- event list
- timeline slider
- chart cursor

This is the most important decision in the feature. Without one clock, the animation becomes decorative rather than analytical.

## What Gets Logged As Events

The engine currently emits high-signal events such as:

- vessel arrival into berth queue
- vessel berthing
- vessel switch-over from discharge to load
- load window opening
- vessel departure
- train departure
- yard congestion threshold crossing
- gate queue spike
- export rollover
- gate open/close transitions

The event stream is intentionally curated. It is not meant to include every container state change.

## Current Scope

The MVP playback view shows:

- animated schematic flows
- berth and anchorage vessel state
- yard block fill
- queues and utilization
- event bookmarks
- synchronized plots with click-to-seek
- configurable playback speed

It does not yet show:

- individual pathing for every container
- 2D yard lane routing
- fully spatial truck trajectories
- advanced camera modes or historical compare-over-compare playback

## Future Direction

The next likely improvements are:

1. filter playback by vessel, block, mode, or container type
2. add anomaly bookmarks generated from KPI thresholds
3. show side-by-side playback for baseline vs scenario
4. replace the SVG renderer with a canvas/WebGL map if scale demands it
