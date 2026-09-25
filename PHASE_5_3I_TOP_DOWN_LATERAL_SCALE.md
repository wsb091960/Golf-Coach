# Phase 5.3I — Correct Top-Down Lateral Scale

## What changed

- The top-down chart now uses separate forward-distance and lateral-distance scales.
- Lateral grid lines are labeled every 20 yards left and right.
- The lateral field displays at least 40 yards on each side of the target line and expands for larger misses.
- A 30-yard miss is now plotted about three-quarters of the way from the target line to the appropriate side of a ±40-yard field.
- Offline labels and the selected-shot metric now include `L` or `R`.

The separate axis scales are intentional and clearly labeled. They make dispersion readable without changing the saved carry or offline measurements.

## Included cumulative fixes

- Phase 5.3E printer-friendly green and gold report.
- Phase 5.3F persistent Alpha database configuration.
- Phase 5.3G restored manual shot-metric entry.
- Phase 5.3H automatic carry/outcome estimates and existing-shot backfill.
