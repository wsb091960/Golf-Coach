# Online instruction pilot — GCDevLog #21

This development slice supports an invite-only asynchronous lesson cycle. It is
disabled by default and does not activate a public offering, billing, email,
automatic AI advice, or student access to the owner workspace.

## First lesson

1. The owner opens **Online Instruction**, selects an existing student, and
   copies a one-use private access link. Share it privately with that student.
   Creating a link does not send a message. Links expire in seven days.
2. The student opens the link on their own device and explicitly accepts it.
   Their secure session lasts up to 14 days. The coach issues a fresh link for
   another device or lost access. This is invitation access, not email verification.
3. The student provides a goal, club, handedness, typical miss, practice access,
   and optional movement considerations. A linked coaching session is created.
4. The student uploads individual swings or screenshots, labels the camera
   view, and submits. Onform, Google login, and a launch monitor are optional.
5. The coach reviews evidence in the queue, opens the associated coaching
   session if needed, saves private notes and a lesson draft, attaches a recorded
   analysis, and explicitly publishes the student summary, priority, drills, and
   practice test. Text-only delivery is also supported.
6. The student opens the published lesson and sends questions/practice results.
   A follow-up creates a separate submission linked to the earlier lesson.

Published lessons are snapshots: later draft changes do not alter what a student
sees. Earlier published versions remain available. Only published recordings are
student-accessible. The owner can revoke all invitations/sessions for a student.

## Configuration before any real invitations

- Keep `ONLINE_INSTRUCTION_ENABLED` unset for the live app until the isolated
  development pilot and storage/restore checks pass. Set it to `1` on a test
  service to enable both routes and the owner navigation item.
- Set `ONLINE_INSTRUCTION_MEDIA_DIR` to an absolute directory on verified
  private persistent storage, e.g. `/var/data/online-instruction`. No upload
  fallback into the repository or ephemeral app directory exists. The code
  requires an absolute path; operators must verify that it is actually on a
  persistent disk, has enough space, and is included in backups.
- Keep the SQLite database on the same approved durable data setup using the
  existing `DATABASE_URL` setting. The new tables use additive `create_all` and
  do not change existing Student or CoachingSession columns.
- Set `GOLF_PUBLIC_URL` to the exact HTTPS origin students and the coach will
  use. Existing same-origin mutation checks also apply to student forms and
  invitation redemption. Secure cookies require HTTPS.
- Confirm original files and database references survive redeploy/restart and
  restore together before enrolling actual students. This branch does not merge,
  activate, or resolve the older R2 storage PR #31. Persistent disk is a bounded
  pilot option; R2 integration remains separate work.
- Agree on a response target and media retention/deletion procedure before
  opening the service. No turnaround promise, prices, or automatic expiry of
  lesson evidence is presented to students.

## Boundaries and validation

Student sessions authorize only `/learn` and never authorize existing coach,
session, or legacy media routes. Student record ownership is checked on every
submission, message, follow-up, and media request. Invitation redemption is
atomic and one-use. Authenticated mutations require the existing same-origin
check. Sensitive responses are not cached and send no referrer.

Files stream in bounded reads, use server-generated names, keep SHA-256/size
provenance, and are delivered through authorized routes. Basic file signatures
and extensions are checked; no arbitrary active formats are accepted. Videos
are limited to 100 MB, images to 10 MB, and evidence to six files per review.
Retrying an identical file/view reuses evidence rather than duplicating it.
Interrupted uploads restart that file; there is no resumable chunk protocol.

Run from the repository root:

```bash
python -m pytest -q tests/test_online_instruction.py
node --check app/static/js/online_instruction.js
git diff --check
```

Before a real pilot, additionally test phone/iPad/desktop file selection,
MP4/MOV playback and seeking, broken connections/retries, owner invite and revoke,
two-student separation, draft/privacy boundaries, and a complete follow-up.
Use synthetic records and a test service for this verification.

## Remaining work

- Integrated annotation/recording, automatic P-position/OCR processing of portal
  uploads, and embedding this evidence in the existing analysis/report pipeline.
  Evidence currently plays in the online review page with a linked coaching
  session; it is not silently inserted into legacy video-storage paths.
- Email/lesson-ready notifications, scheduling, due dates, memberships, checkout,
  credit accounting, independent account recovery, and self-service export/deletion.
- A storage quota/retention interface, orphan reconciliation after deletion of
  legacy students/sessions, and media migration/object-storage integration.
- Back up portal evidence before deleting legacy student/session records; this
  pilot denies access after student deletion but does not automatically delete
  its private files. Do not turn it into a public paid service before the
  required lifecycle and storage controls are ready.
