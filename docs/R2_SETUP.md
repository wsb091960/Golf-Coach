# External media storage for Golf Coach

R2 support is opt-in. This change prepares private video and screenshot storage;
it does not create a Cloudflare account/bucket, activate billing, migrate live
files, or rewrite Git history. The default remains local until configured.

## Enable the storage account

1. Open the [Cloudflare dashboard](https://dash.cloudflare.com/), select
   **Storage & databases > R2 > Overview**, and enable R2. Its checkout flow may
   require billing details. Review the usage-based terms there.
2. Create a **private Standard storage** bucket, for example `wsbco-golf-media`.
   Leave public access and the public development URL disabled. Use a different
   private bucket for podcast masters, for example `busterball-media`.
3. Create an R2 S3 token with **Object Read & Write**, scoped to the Golf Coach
   bucket. Save the Access Key ID and Secret Access Key directly in the app's
   hosting settings; do not paste them into chat or source files. Use separate
   credentials for the podcast bucket.

The two projects share the account's free allowance; each bucket does not get a
separate 10 GB allowance. Check current [R2 pricing](https://developers.cloudflare.com/r2/pricing/).

## Configure Golf Coach on Render

Use the existing `Golf-Coach` service in William's workspace, then its
**Environment** settings. Add these settings without removing existing ones:

| Setting | Value |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare's 32-character account ID |
| `R2_BUCKET` | The private Golf Coach bucket name |
| `R2_ACCESS_KEY_ID` | Secret credential from R2 |
| `R2_SECRET_ACCESS_KEY` | Secret credential from R2 |
| `R2_PREFIX` | `golf-coach` (keep stable once media is saved) |
| `MEDIA_STORAGE_BACKEND` | `r2` when ready to enable new remote writes |

Deploy the reviewed source with `MEDIA_STORAGE_BACKEND=local` first if staging
the code before the account is ready. Configure and test R2 with synthetic data
before enabling real student uploads. A backend of `r2` with incomplete settings
is an error; it will not silently continue saving new uploads locally.

Private media stays behind the existing owner-authenticated app routes. The app
streams R2 content with byte-range support for seeking, retaining same-origin
canvas/OCR access without making the bucket public. **Render outbound bandwidth
still applies** to this proxy; R2's free egress does not waive Render's own
transfer charges. A future direct signed-delivery option can reduce that traffic
after its CORS and private-access behavior are tested. No R2 browser CORS setting
is needed for the current server-mediated delivery path.

Do not change the bucket/prefix or discard the credentials after saving remote
media. Existing unmarked file references require the R2 backend for remote reads;
switching back to local is not a complete rollback after real remote uploads.
Restore originals or keep remote reads configured before changing write modes.

## Existing files: copy, verify, retain

Run migration where the **actual files exist**, not a clean Git checkout. Pause
writes and back up SQLite plus media before migration. The existing paths are
`app/media/session_videos` and `app/media/onform_screenshots`. The current code
uses those paths in the app tree; a Render disk mounted at `/var/data` does not
automatically make them persistent. Inventory before any redeploy that could
replace ephemeral local files.

```sh
python scripts/migrate_media_to_r2.py --manifest /var/data/media-inventory.json
python scripts/migrate_media_to_r2.py --apply --manifest /var/data/media-copy.json
```

The first command only inventories and needs no credentials. The second copies
each file to the matching category/name key, verifies downloaded SHA-256 bytes,
and retains all originals. It stops on conflicting objects and writes a private
manifest as progress is made. The script neither changes database references nor
deletes source files. Existing filename references stay valid with R2 enabled.
This command covers filesystem video/Onform images, not SQLite image blobs.

New session screenshots and P-sheets can also store compact R2 references in
their existing database columns; legacy raw-byte rows remain readable. Existing
database image blobs require a separate verified migration before the SQLite
file can shrink. Whole-student/session object retention and orphan cleanup need
an explicit retention procedure; no bulk object deletion is added here.

## Acceptance before removing any original

- Upload one test screenshot and one video; confirm private viewing, pause,
  forward/backward seeking, downloads, and re-opening the session.
- Confirm screenshot OCR rereads and AI lesson/P-sheet analysis still resolve the
  original image bytes. Check that image references, metrics, and sessions persist.
- Confirm a logged-out browser cannot retrieve student media.
- Confirm a redeploy retains access and restore one migrated file from R2.
- Compare actual GitHub/Codespaces/Actions usage with its limit. Ignoring new
  media does not reclaim existing artifacts, LFS objects, or historical Git blobs.

No repository history rewrite, old artifact deletion, or original-media deletion
is included in this change. The checked-out Golf Coach source is small; the exact
reported account quota has not yet been identified.

## Podcast

The companion BusterBall_Podcast change uploads generated WAV files to its own
private R2 bucket and retains a small reference manifest in GitHub Actions.
Image/video uploads use the same uploader. It must be configured before merging
the workflow switch. Public RSS hosting needs a separately approved public
delivery bucket/domain and stable episode URLs; it is not enabled by this work.

References: [R2 setup](https://developers.cloudflare.com/r2/get-started/),
[R2 S3 credentials](https://developers.cloudflare.com/r2/api/tokens/),
[Python SDK](https://developers.cloudflare.com/r2/examples/aws/boto3/).
