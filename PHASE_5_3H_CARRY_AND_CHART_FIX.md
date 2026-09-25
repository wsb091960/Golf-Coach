# Phase 5.3H — Carry Calculation and Chart Fix

## What changed

- Manual shots now estimate carry when Carry is blank and Ball Speed or Club Speed is available.
- Missing Total, Apex, and Offline outcomes are estimated from the available shot inputs.
- Existing manual shots with speed data are backfilled automatically the next time their session page opens.
- Estimated manual shots are stored as `Manual Entry · Estimated Outcomes` and marked `est.` in the shot table.
- Ball-flight charts no longer substitute a fake 1-yard carry.
- If there is not enough information to calculate carry, both flight charts show a clear `Carry unavailable` message.
- Chart descriptions now distinguish measured values from calculated visual estimates.

## Example validation

- Driver at 150 mph ball speed: estimated carry 247.5 yd.
- Driver at 170 mph ball speed: estimated carry 280.5 yd.

Launch angle and spin rate refine these estimates when supplied. Calculated values are coaching estimates, not launch-monitor measurements.

## Included cumulative fixes

- Phase 5.3E printer-friendly green and gold report.
- Phase 5.3F persistent Alpha database configuration.
- Phase 5.3G restored manual shot-metric entry.
