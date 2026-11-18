# Your animated GitHub profile

This package is prepared for **parthsmart / Parth**. Published at https://github.com/parthsmart.
The profile README request returned 404. You did not provide a personal website, so the proposed palette is blue `#60A5FA`, teal `#2DD4BF`, and amber `#FBBF24`, on a dark `#161B22` background with light text. Fonts are Lato Regular and Lato Bold.

Trendz-Tracker is your confirmed feature. AI Navigator and MistakeMemo are provisional picks from your public projects; their READMEs describe a learning-roadmap tool and a debugging-memory tool. I could not verify their relationship to your latest hackathons, so no event or award claims are included. The Trendz Abacus tile currently links to Trendz-Tracker; change that URL if you have a separate Abacus site.

## 1. Make your profile repository

On GitHub, create a **public** repository named `parthsmart`, under your `parthsmart` account. GitHub displays the README from a public repository whose name exactly matches your username. If this repository already exists but the connector could not access it, use that repository and keep a backup of its README.

Clone it to your computer, or download it and open the folder in your editor. Copy the contents of this package into that folder, including the hidden `.github` folder. Keep `render_cards.py` at the repository root. The package contains:

```text
render_cards.py                 The only Python script you need
requirements.txt               Font subsetting dependency
README.md                      Generated GitHub profile layout
.github/workflows/cards.yml    Daily refresh job
assets/fonts/                  Original fonts and their license
cards/                         Nine generated SVG cards and a local preview
data/contributions.json        Labeled demo data, replaced by the live refresh
```

## 2. Personalize the short settings block

Open `render_cards.py`. The settings near the top control your name, tagline, colors, links, and featured repositories. The tagline is a proposed line, not copied from an existing bio.

- `FEATURED`: each row is `(repo name, display title, description, label)`. Replace AI Navigator or MistakeMemo when you choose your hackathon entries.
- `TILES`: each row ends with the destination URL. These links wrap the images in the README; links inside an SVG image would not be clickable.
- `WEBSITE`: leave empty, or add your personal website URL.
- `PORTRAIT`: leave empty for the P monogram. To add a portrait, put a small PNG/JPG in `assets/`, then enter its relative path. It is embedded so no external image fetch is needed.
- Keep titles and descriptions short. This simple fixed layout deliberately does not shrink long text to unreadable sizes. Check your preview after edits.

## 3. Install Python and the font tool

Install Python 3.12 if needed. Open a terminal **inside the repository folder**. On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The full fonts and license are included. If a font is missing, the script downloads it from Google Fonts once. Keep these files in the repository so later builds use the same font files. The script checks each font's **name table**, upright/italic flags, angle, weight, and glyph coverage. It then runs the `pyftsubset` module for each card and embeds only that card's characters as base64 WOFF.

## 4. Preview the finished frame before pushing

The supplied preview is explicitly marked **DEMO DATA**. Its numbers are made-up examples for reviewing the layout, not your GitHub activity. Demo generation does not overwrite your live contribution JSON.

Windows PowerShell:

```powershell
$env:STATIC = "1"
.\.venv\Scripts\python render_cards.py --demo --out preview-static
Start-Process preview-static\preview.html
```

macOS/Linux:

```bash
STATIC=1 .venv/bin/python render_cards.py --demo --out preview-static
# Open preview-static/preview.html in your browser.
```

Take your screenshot from that page. `STATIC=1` omits animation rules entirely and shows the final geometry immediately. This separate preview folder keeps the publishable cards intact.

To preview animation on Windows:

```powershell
Remove-Item Env:STATIC -ErrorAction SilentlyContinue
.\.venv\Scripts\python render_cards.py --demo
Start-Process cards\preview.html
```

## 5. Upload and run the daily workflow

Commit and push the files to `main`. With Git installed, from the repository folder:

```bash
git add README.md render_cards.py requirements.txt .gitignore .github assets cards data SETUP.md
git commit -m "Add animated profile cards"
git push origin main
```

GitHub's **Actions** tab should show **Refresh profile cards**. Open it and choose **Run workflow** if it has not started. The workflow:

1. Uses GitHub's built-in token to request your contribution calendar.
2. Saves real counts to `data/contributions.json`.
3. Runs the renderer, which reads that JSON and creates the cards.
4. Updates README links and removes the demo notice.
5. Commits only if the generated files changed.

No personal token is needed for the default public contribution view. The job declares `contents: write` to commit the cards. If it cannot push, check repository **Settings → Actions → General → Workflow permissions**, and any branch protection rules. A protected branch may require a separate pull-request workflow or permission for this bot; the supplied job does not bypass protection.

The daily schedule is **07:53 India time (02:23 UTC)**. GitHub may delay scheduled runs. Scheduled workflows run from the default branch and can be disabled after 60 days without repository activity. You can re-enable the workflow from Actions. If your default branch is not `main`, update the `push.branches` entry; scheduled and manual runs already check out the default branch.

Optional: if you deliberately need a different contribution visibility scope, add a repository Actions secret named `PROFILE_TOKEN`. The workflow uses that instead of its built-in token. Keep credentials in GitHub Secrets, never in the Python script, README, or JSON. Any counts returned by that credential will be written into your public repository; private contribution visibility depends on your GitHub settings and token access.

## 6. Use real data locally

After the workflow succeeds, run `git pull` to get `data/contributions.json`. You can then render offline:

```powershell
.\.venv\Scripts\python render_cards.py
$env:STATIC = "1"
.\.venv\Scripts\python render_cards.py --out preview-static
Remove-Item Env:STATIC
```

For a live local refresh, securely set `GH_TOKEN` in your terminal, then run `python render_cards.py --refresh` using your virtual environment's Python. That command only fetches and saves data. Run the script again without `--refresh` to render. Missing or invalid data fails loudly instead of silently publishing fake statistics. API failures leave the previous JSON untouched.

## How the statistics work

The window starts on the first day of the month eleven months before the current UTC month and ends today. There are exactly twelve monthly bars, with the current month marked as partial. The graph and statistics use that same window.

- **Contributions** are GitHub calendar contributions, not just commits.
- **Active days** are dates with a count greater than zero.
- **Current streak** counts consecutive active dates ending today, or yesterday if today is still zero. It is limited to the displayed window.
- **Busiest day** is the individual date with the largest count; the earliest date wins ties. All-zero data says “No activity yet.”

The saved dates are GitHub's returned calendar dates and the query bounds are UTC. Statistics may differ from a third-party streak service using another date window or timezone.

## Animation and accessibility

The hero enters first, followed by the graph, monthly bars, three tiles, and featured repositories. All animations are short, run once, and leave readable final content. Images each have their own load clock, so staggered delays approximate top-to-bottom playback; separate SVG images cannot share an exact synchronized timeline.

This implementation uses inline CSS keyframes, which work in SVG image context, and no JavaScript, external CSS, or external fonts. SMIL is intentionally unnecessary: CSS can completely disable every animation under `prefers-reduced-motion`, while a CSS media query cannot stop a SMIL timing timeline reliably. If you meant SMIL to be mandatory, that conflicts with a strict “every animation off” rule without an extra static-image selection layer. Here the reduced-motion requirement takes priority. With reduced motion enabled, the final frame appears immediately.

Every README image has alt text; each SVG has a title. The preview uses `<img>` elements rather than inline SVG, matching the important rendering restrictions on GitHub. GitHub image caching can delay a visible update. Embedded WOFF rendering can vary by image viewer; an Arial/sans-serif fallback remains available.

## References

- [GitHub profile README requirements](https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme)
- [GitHub GraphQL users and contributions](https://docs.github.com/en/graphql/reference/users)
- [FontTools pyftsubset options](https://fonttools.readthedocs.io/en/latest/subset/)
- [Lato Regular source and license](https://github.com/google/fonts/tree/main/ofl/lato)
- [SVG image restrictions](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/SVG_as_an_image)
- [Reduced-motion media query](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion)
- [Scheduled workflow inactivity](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)
