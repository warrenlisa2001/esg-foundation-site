# Deploying the ESG Foundation site

The zip you have includes a ready-to-go git repo (already `git init`'d and committed on branch `main`) — you just need to point it at GitHub and connect Cloudflare Pages.

## 1. Push to GitHub

1. Unzip the folder and open a terminal inside it (the `.git` folder is already there — don't re-run `git init`).
2. Go to https://github.com/new and create a **new, empty repository** (no README, no `.gitignore`, no license — those would conflict with the existing commit). Name it whatever you like, e.g. `esg-foundation-site`.
3. Copy the repo URL GitHub gives you, then run:

```bash
git remote add origin https://github.com/<your-username>/esg-foundation-site.git
git push -u origin main
```

That's it — your code is on GitHub.

## 2. Deploy on Cloudflare Pages

This is a static HTML site, so there's no build step at all.

1. In the Cloudflare dashboard, go to **Workers & Pages → Create → Pages → Connect to Git**.
2. Authorize Cloudflare to access your GitHub account if prompted, then select the `esg-foundation-site` repo.
3. On the build settings screen:
   - **Framework preset:** None
   - **Build command:** *(leave empty)*
   - **Build output directory:** `/`
4. Click **Save and Deploy**. Cloudflare will give you a `*.pages.dev` URL within a minute or two.
5. (Optional) Under the Pages project's **Custom domains** tab, add `esgfoundation.org` (or whichever domain you want to point at it) and follow the DNS instructions Cloudflare shows you.

From then on, every `git push` to `main` auto-redeploys the site — no extra steps.

## Notes

- All photography on the site is hotlinked from Unsplash (free license, no attribution required, but photo credits are included in a couple of places anyway). Once this is live and reachable from a normal browser, double-check the images load the way you expect — I built and verified the HTML/CSS in a sandboxed environment with no internet access, so I could confirm the markup is correct but never actually saw the photos render.
- The site has no backend/database — the "Submit a Report" flow opens a pre-filled email rather than writing to a form handler, since there's nowhere for it to go on a static host. If you later want real submission handling, Cloudflare Pages Functions or a simple form service (e.g. Formspree) would be the natural next step.
