WSBCO Golf Coach — Phase 5.3B7
Source-Derived Page-Shell Recovery

This repair was built from Golf_Coach_Current_Source_Diagnostic.zip, created
from the installed development application on September 17, 2026.

Confirmed causes repaired:
- At widths of 992px or less, the legacy .app-shell remained a two-column
  grid after its sidebar moved off-canvas. Students, Sessions, Garmin Import,
  Analysis, and older swing pages were therefore trapped in a 252px column.
- The rule that moved the sidebar off-screen had greater CSS specificity than
  the rule that opened it. The hamburger JavaScript worked, but the sidebar
  remained visually hidden.

This update:
- Makes the legacy shell a true one-column block at narrow/split-screen widths.
- Gives the open state sufficient specificity and an explicit transform.
- Preserves the full-screen fixed green navigation.
- Preserves the removed page-title/profile header.
- Preserves the gold Dashboard illustration.
- Preserves the Coaching Assistant plan formatting and AI connection.
- Preserves Empty session cleanup.
- Preserves Delete selected session, which permanently removes the selected
  session and its dependent shots, videos, messages, and assessments.
- Changes no database file and no student/session data during installation.
- Makes a timestamped backup before replacing source files.

INSTALL
1. Upload the ZIP into /workspaces/Golf-Coach.
2. Stop Uvicorn with Ctrl+C.
3. Run:

   cd /workspaces/Golf-Coach
   unzip -o Golf_Coach_Phase_5_3B7_Source_Derived_Recovery.zip
   python phase_5_3B7/install.py
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

4. Hard-refresh the browser with Ctrl+Shift+R.

VERIFY
- At full width, the green navigation remains visible on the left.
- In a split/narrow window, click the hamburger. The green navigation opens.
- Students and Sessions use the full available page width.
- To remove a stranded session, open Coaching Assistant, select it under
  Delete a session permanently, and confirm deletion.
