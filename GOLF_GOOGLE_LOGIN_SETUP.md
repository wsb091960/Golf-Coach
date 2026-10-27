# Golf Coach owner-only Google sign-in

This branch adds a Google sign-in gate to all Coaching Portal routes and keeps the public golf homepage available. It reuses the CRM's private Google Apps Script bridge with a separate signing key and audience for Golf-Coach.

## Before enabling the live gate

1. Merge the companion `feature/google-login-golf-app` branch in `WSBCO-CRM`, then update the existing Google Apps Script web-app deployment to that version. Keep **Execute as: User accessing the web app** and **Who has access: Only myself**.
2. In the Apps Script project's Script Properties, add `GOLF_GOOGLE_SIGNING_KEY` with a new random value of at least 32 characters. Do not reuse the CRM signing key and never commit the key.
3. Add these Render environment variables to the Golf-Coach service:
   - `GOLF_GOOGLE_LOGIN_URL`: the same deployed Apps Script `/exec` URL used by CRM
   - `GOLF_GOOGLE_SIGNING_KEY`: the exact matching key from Script Properties
   - `GOLF_OWNER_EMAIL`: the owner's exact Google email (default is `williamsburton@gmail.com`)
   - `GOLF_PUBLIC_URL`: `https://www.busterball.com`
4. Deploy the Golf-Coach branch after the Render values and Apps Script update are in place. Missing authentication configuration fails closed for the portal; the public homepage stays available.

Google signs only the verified owner identity. The bridge sends a two-minute, one-use HMAC assertion by HTTPS POST. The app binds it to a one-use browser challenge, stores only hashes of random 12-hour sessions, sets Secure/HttpOnly/SameSite cookies, checks same-origin mutations, rate-limits login starts, and denies all app/API/docs routes by default until authenticated.
