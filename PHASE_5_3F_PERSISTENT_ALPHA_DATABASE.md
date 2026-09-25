# Phase 5.3F — Persistent Alpha Database

## Problem corrected

Alpha previously stored SQLite at `app/data/golf_coach.db`. Render's normal
service filesystem is temporary, so the database was recreated after each
deployment or restart.

Phase 5.3F makes `app/database.py` honor the `DATABASE_URL` environment
variable. Local development still defaults to `app/data/golf_coach.db`.

## Required Render configuration

Complete these steps before entering real student data:

1. Open the `WSBCO-Golf-Coach` web service in Render.
2. If the service uses the Free plan, upgrade it to a paid web-service plan.
   Render persistent disks are not available on Free web services.
3. Open **Disk** and add a disk with:
   - Name: `golf-coach-data`
   - Mount path: `/var/data`
   - Size: the smallest available size is sufficient for the SQLite database.
4. Open **Environment** and add:
   - Key: `DATABASE_URL`
   - Value: `sqlite:////var/data/golf_coach.db`
5. Save the environment change and deploy the latest commit.

The first deployment creates a new database on the persistent disk. Every
later deployment reuses the same database file.

## Important

- Do not enter permanent student data until the disk and environment variable
  are configured and the persistent deployment is live.
- A Codespaces secret or `.env` file does not configure Render.
- Only content written under `/var/data` is protected by this disk.
- Session videos and Onform screenshots currently use separate application
  folders and should be moved to persistent storage in the next storage phase.

## Verification

1. Add a temporary test student in Alpha.
2. Trigger a new Render deployment.
3. Reopen Alpha after the deployment becomes live.
4. Confirm that the test student is still present.
5. Only then begin entering permanent student information.
