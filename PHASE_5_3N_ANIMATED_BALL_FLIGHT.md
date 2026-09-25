# Phase 5.3N — Animated Ball Flight

## What changed

- Added an animated 2.5D driving-range replay for the selected shot.
- Added Behind, Side, and Overhead camera angles.
- Added Replay, Pause/Resume, and 0.5x/1x/2x speed controls.
- Added an animated tracer plus landing, bounce, and roll phases.
- Added live distance, height, offline, and model-status readouts.
- Labeled incomplete launch-monitor data as an estimated flight model.
- Removed the redundant standalone top-down flight card.
- Kept compact selected metrics, shot-table dispersion, and delivery geometry below the replay.

## Modeling note

The replay is fitted to stored carry, total distance, apex, offline distance,
launch direction, spin axis, and face-to-path when those fields are available.
It is a coaching visualization, not an independent launch-monitor measurement.
