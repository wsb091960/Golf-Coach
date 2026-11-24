# WSBCO Golf Simulators

November 23, 2026 (America/Los_Angeles)

The first release packages the existing Ball Flight and D-Plane simulators as a
single installable web app. Entry: `/static/simulators/index.html`, also linked
from the Golf Coach sidebar as **Install Golf Simulators**.

## Install and use

Open the entry page online. On iPad, use Safari's Share menu and Add to Home
Screen (enable Open as Web App if offered). On Android, use Chrome's Install
app/Add to Home Screen option. Wait for **Available offline** before disconnecting.
Open each simulator once in airplane mode on the actual device to confirm.

Both simulations, replay/camera controls, the existing local Laws & Principles
interpretation, and saved demonstration presets run on the device. No paid API,
new account, backend resource, or additional runtime package is introduced.
Presets are local to this browser/device. They are not student records, are not
synced or backed up, and can be lost when browser data is cleared. Save/load/delete
supports up to 30 named examples per simulator and reports blocked/full storage.

Reference links and the Golf Coach dashboard require internet. The portable
pages do not include the server-backed coaching assistant. Existing private
student/session features and normal simulator routes retain their current auth.
The manual simulator assets are intentionally served through the existing public
static mount. No student/session/CRM data is included or downloaded.

## Build and cache design

Run `python scripts/build_portable_simulators.py` after editing simulator source.
Jinja2 is already an application dependency. The builder renders the same source
templates against a portable shell and copies the same engines and styles into
`app/static/simulators/`. Generated output is committed, so the existing Render
build/start commands do not need changes. Run with `--check` to detect stale output.

The manifest and service worker have scope `/static/simulators/`. The worker
precaches an explicit, complete file list under a content-derived version. It
does not intercept or cache any other Golf Coach URLs. A failed first download
never reports readiness. Retrying can repair missing cache entries. A new version
waits until the user chooses **Update ready · reload**, then removes only older
caches belonging to this exact simulator scope. Updates never clear local presets.
The cache is not a guaranteed permanent backup; device/browser eviction remains
possible. Keep a way to download the app again when online.

## Validation

`python scripts/build_portable_simulators.py --check`

`node tests/portable_simulators.test.cjs` (Playwright with Chromium installed)

Set `PLAYWRIGHT_EXECUTABLE_PATH` to use an existing Chromium binary when needed.
The browser test starts its own local HTTP fixture and covers offline reopening,
both engines, local presets across reloads, manual-distance preservation,
landscape/portrait tablet and phone widths, no external dependencies, interrupted
installation/retry, cache eviction repair, and explicit version activation.
GitHub Actions runs the same checks and captures layout screenshots.
Actual Safari/iPad and physical Android installation remain device acceptance
checks; Chromium viewport emulation does not establish Safari compatibility.

## Direction: field client and central processing

William's direction: phones/tablets collect field data; the central Golf Coach
database provides advanced processing and AI analysis after connection. This is
the next phase, not a capability of this first simulator release.

Preserve the installable shell and standalone simulation engines as its foundation.
Add an authenticated capture/sync layer rather than treating demonstration presets
as student records. Proposed boundaries:

1. **Capture:** explicitly choose a student/session and individual swing. Save
   shot metrics with units, notes, evidence, capture time, source, review status,
   schema version, and a device-generated UUID in IndexedDB. Keep measured,
   hypothetical, and AI-derived values distinct.
2. **Outbox:** durable pending uploads with per-item queued/uploading/synced/error
   states. Show the last successful sync and retry failures on reconnect or when
   the user opens the app. Do not depend solely on background execution.
3. **Server ingest:** authenticated, authorized endpoints verify student/session
   ownership and deduplicate by UUID/idempotency key. Use record revisions and
   explicit conflict handling; never silently overwrite a coach-reviewed record.
4. **Evidence:** checksum-verified resumable media upload into the approved private
   storage workflow. Mark evidence complete only after server acknowledgement.
   Preserve local originals until verified; offer deliberate retention/cleanup.
5. **Analysis:** queue server processing after verified sync. AI credentials stay
   on the server; results retain input versions, source evidence, uncertainty,
   model/version and coach approval before becoming GCIE LKM knowledge.

This phase requires API/data-model design and a real offline-to-online acceptance
test, including session expiry, duplicate retries, conflicts, and interrupted
media transfers. No capture API, field-data synchronization, AI call, or database
migration is implemented by the portable simulator package.
