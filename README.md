# Staccato Employee Board

A static rebuild and redesign of the Staccato 2011 Employee Board, which used to run as a WordPress theme on WP Engine. It's plain HTML, CSS and JavaScript with no build step and no server, so it can be hosted on GitHub Pages.

## Views

| URL | What it shows |
|---|---|
| `/` | **Board**: a rotating grid of employee cards with tenure, veteran and birthday badges, core values, this month's work anniversaries, recent hires, and a news ticker |
| `/?tv=1` | **TV / kiosk mode**: the Board with the on-screen controls hidden, for lobby and break-room screens |
| `/?tv=1&interval=30` | Seconds per page (default 20) |
| `/#directory` | **Directory**: search, filter by department, and sort by name or tenure |

## Content

All content lives in two JSON files:

- `data/employees.json`: `name, title, department, hireDate (YYYY-MM-DD), photo, service, featured, birthday (MM-DD)`
  - `birthday` is month and day only, never the year. It shows on Directory cards, adds a Happy Birthday badge on the day, and feeds the Today's Birthdays panel
  - `service` sets the veteran badge: `Army`, `Navy`, `Air Force`, `Marines`, `Coast Guard`, `Space Force`, `Military`, `Law Enforcement`, `Emergency Services`
  - Each branch badge has its own color, set by the `.svc-*` classes in `styles.css`. Branch seals live in `assets/branches/` and are set with `logo` in the `SERVICE` table at the top of `app.js`
  - Tenure and anniversaries are calculated automatically from `hireDate`
  - Employees with no `photo` get a monogram card
- `data/bulletins.json`: `title, type, expires, html`
  - `type`: `alert` goes to the ticker. `info`, `event` and `big` each get a panel in the side rail
  - A bulletin with an `expires` date disappears after that day
  - A bulletin titled "Core Values" is shown in the rotating values panel

To edit content, change the JSON and commit. GitHub Pages redeploys in about a minute.

### Syncing with Paylocity

Export from Paylocity with the columns FirstName, LastName, JobTitle, HireDate, BirthDate and Veteran Status, then run:

    pip3 install openpyxl                                   # once
    python3 scripts/sync_paylocity.py ~/Downloads/Paylocity_Data_Dump.xlsx           # preview
    python3 scripts/sync_paylocity.py ~/Downloads/Paylocity_Data_Dump.xlsx --write   # save

The sync updates titles, birthdays and veteran status, and adds anyone new. It never removes anyone, and it keeps the board's names, hire dates and photos. The rules it follows are in `data/paylocity_overrides.json`:

- `titleFixes` / `nameFixes`: spelling corrections applied every run, so Paylocity typos don't come back
- `match`: people whose name or hire date differs between Paylocity and the board
- `exclude`: people who were removed from the board and shouldn't be added back. When you remove someone, add their name here too

### Regenerating from WordPress

    python3 scripts/build_data.py path/to/WordPress-export.xml

This script also cleans up department names. For example, `910 - OPS- Machine Shop` becomes `Machine Shop`, and stray numeric IDs are removed.

### Photos (Azure photo pipeline)

Photos aren't stored in Git. Originals are archived in Azure Blob Storage under `assets/photos/<id>.<ext>`. Optimized copies (960px WebP, about 60 KB each) are under `assets/photos-rendered/<id>.webp`, and the board loads them from the storage account's web address set in `data/config.json`. `data/employees.json` stores the original's path, for example `assets/photos/938.jpg`. If `config.json` is missing, cards show the no-photo design.

**The photo address is public.** Anyone who has it can open the photos, so delete a departed employee's files from the container when you remove them from the board. The sync never deletes anything.

Setup (once):

    brew install uv                 # or see docs.astral.sh/uv
    uv sync --locked
    cp .env.example .env            # then fill in the Azure values

Adding or replacing a photo:

1. Save the original as `assets/photos/<id>.jpg` (or .png). `<id>` is the person's `id` in `data/employees.json`.
2. Set their `photo` field to `assets/photos/<id>.jpg`.
3. Preview the upload, then upload it:

        uv run python scripts/sync_photos.py push --dry-run
        uv run python scripts/sync_photos.py push

    The push renders the WebP copy and uploads both versions.
4. Commit and push `data/employees.json`.

Other commands:

- `uv run python scripts/sync_photos.py pull` downloads the originals and WebP copies to your machine.
- `uv run python scripts/render_photos.py` renders WebP copies locally. Preview them at `http://localhost:8000/?photos=local`.
- `uv run python scripts/configure_frontend.py` regenerates `data/config.json` after changing `AZURE_WEB_URL` or the rendered-photo folder.
- `uv run python -m unittest discover -s scripts -p 'test_*.py'` runs the photo tests.
- `uv run scripts/localize_photos.py` downloads photos still on the old WordPress site into `assets/photos/`. Run `sync_photos.py push` afterwards.

### Veterans Day

On November 11 the Anniversaries and Welcome Aboard/Birthday panels are replaced by a green "Thank You, Veterans" panel. It lists everyone with a veteran status, with their photo, branch and branch seal, and rotates pages if they don't all fit. To preview it on any day, add `?veteransday=1` to the URL.

## Run locally

    python3 -m http.server 8000   # then open http://localhost:8000

## Privacy note

This site shows employee names, photos, titles, hire dates and veteran status. **GitHub Pages sites are public** unless the org is on GitHub Enterprise Cloud, which can restrict Pages to org members. `noindex` is set, but that only keeps the site out of search results; it doesn't stop anyone with the link from viewing it. Before sharing the URL, confirm with HR that public hosting is acceptable.
