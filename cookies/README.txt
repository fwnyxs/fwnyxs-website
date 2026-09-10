FWNYXS LANDING PAGE V1 — NETLIFY READY

Includes:
- Kinetic "THE SIGNAL" hero
- Mobile hamburger navigation
- About / Artist 001 / Releases / Visual Archive / Submit / Mailing List / Contact
- LAIYA link to https://laiya.fwnyxs.my/
- HATED release placeholder, 09.09.2026
- Netlify newsletter form
- Thank-you page
- Custom 404 page
- Privacy + disclaimer + cookies pages
- Cookie consent banner (Accept All / Necessary Only), sitewide, choice remembered in the browser
- OG/Twitter metadata, favicon and Organization JSON-LD
- Reduced-motion support

BEFORE LAUNCH:
1. Replace the LAIYA image placeholder with the approved campaign image.
2. Replace generic social links with official FWNYXS accounts.
3. Add real streaming links when HATED is released.
4. Replace the SVG OG image with a 1200x630 JPG/PNG for maximum social compatibility.
5. In Netlify, enable/confirm Form detection and configure form notifications.
6. For an automatic branded welcome email to subscribers, connect the Netlify form to a server-side email workflow/provider. Keep API keys in Netlify environment variables.
7. The cookies.html page currently states no analytics are running. If you add Google Analytics, Meta Pixel, or similar later, update that page's "What we use today" section and only load the tracking script after fwnyxsCookiePrefs.get() returns {value:'all'} — otherwise the banner is decorative rather than actually gating anything.

Netlify will automatically serve 404.html for unknown URLs.
