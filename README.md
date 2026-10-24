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

- `data/employees.json`: `name, title, department, hireDate (YYYY-MM-DD), photo, service, featured, birthday`
  - `service` sets the veteran badge: `Army`, `Navy`, `Air Force`, `Marines`, `Coast Guard`, `Space Force`, `Military`, `Law Enforcement`, `Emergency Services`
  - Tenure and anniversaries are calculated automatically from `hireDate`
  - Employees with no `photo` get a monogram card
- `data/bulletins.json`: `title, type, expires, html`
  - `type`: `alert` goes to the ticker. `info`, `event` and `big` each get a panel in the side rail
  - A bulletin with an `expires` date disappears after that day
  - A bulletin titled "Core Values" is shown in the rotating values panel

To edit content, change the JSON and commit. GitHub Pages redeploys in about a minute.

### Regenerating from WordPress

    uv run scripts/build_data.py path/to/WordPress-export.xml

This script also cleans up department names. For example, `910 - OPS- Machine Shop` becomes `Machine Shop`, and stray numeric IDs are removed.

### Photos

Photos are archived in `assets/photos/`. After regenerating data from WordPress, copy any remote photos into this repo and update their JSON paths by running:

    uv run scripts/localize_photos.py

### Azure photo sync

Use Azure Blob Storage for long-term photo storage and `assets/photos/` as a local cache excluded from Git. The sync script automatically loads `.env` from the repository root; existing environment variables take precedence. Run `uv sync --locked` to install dependencies.

Configure these variables in a local `.env` file:

```dotenv
AZURE_WEB_URL=<container-web-base-url>
AZURE_PHOTO_PREFIX=assets/photos/
AZURE_RENDERED_PHOTO_PREFIX=assets/photos-rendered/
PHOTO_OUTPUT_PATH=assets/photos-rendered/
PHOTO_MAX_SIZE=960
PHOTO_WEBP_QUALITY=82
AZURE_STORAGE_CONTAINER=<container-name>
AZURE_STORAGE_CONTAINER_CONNECTION_STRING=<connection-string>
```

`.env` and `assets/photos/` are ignored by Git. Copy `.env.example` to `.env` for a new setup. The configured container must already exist.

Preview uploads, then push new or changed local photos to the container:

```powershell
uv run python scripts/sync_photos.py push --dry-run
uv run python scripts/sync_photos.py push
```

Download photos from the container for local use:

```powershell
uv run python scripts/sync_photos.py pull
```

Sync preserves filenames, compares SHA-256 hashes, and never deletes files in either direction. `AZURE_PHOTO_PREFIX` defaults to `assets/photos/` and sets the folder inside the container for both push and pull. Pull restores those files to local `assets/photos/`. Push automatically renders local originals, then uploads both originals and optimized WebP images to their respective prefixes. A push dry run renders into a temporary folder and changes neither the cache nor Azure. Pull downloads both sets. Push replaces changed remote photos; pull protects differing local files unless you pass `--overwrite`. Both commands support `--dry-run`. Failed transfers and unresolved pull conflicts return a nonzero exit status. Previously uploaded container-root photos are left untouched.

The frontend builds optimized photo URLs from `AZURE_WEB_URL` + `AZURE_RENDERED_PHOTO_PREFIX` + the WebP filename, for example `<container-web-base-url>/assets/photos-rendered/123.webp`. Originals remain at `AZURE_PHOTO_PREFIX`, for example `assets/photos/123.jpg`. Keep `AZURE_WEB_URL` as the website root, without the photo prefix. After changing either setting, generate the public configuration:

```powershell
uv run python scripts/configure_frontend.py
```

Commit and publish `data/config.json` with the site. It contains only the public web URL and photo prefix; the connection string stays in `.env`. The browser loads this configuration for all board, milestone, and directory photos. The photo endpoint must allow browser reads.

For local rendered photos after a pull or render, open `http://localhost:8000/?photos=local` (combine with `&tv=1` for kiosk mode). Employee JSON keeps its portable `assets/photos/<filename>` paths. Changing the rendered Azure prefix does not require changing employee data. Regenerate public configuration after changing paths. Publish it after uploading the rendered files.

To render without connecting to Azure:

```powershell
uv run python scripts/render_photos.py
```

Rendering corrects EXIF orientation, converts colors to sRGB, removes embedded metadata, preserves transparency and aspect ratio, and saves WebP at quality 82 with a maximum dimension of 960 pixels. Small images are not enlarged; animated images use their first frame. Source hashes and render settings are cached locally so unchanged images are skipped. Output is written atomically. Duplicate source stems are rejected to prevent filename collisions.

`PHOTO_OUTPUT_PATH` controls the local output folder; `AZURE_RENDERED_PHOTO_PREFIX` controls its Azure destination. Keep both separate from originals. The default output folder is ignored by Git; add an ignore rule if choosing a different folder. No automatic deletion occurs, so removed source images may leave unused rendered files locally and in Azure.

Verify the initial upload before publishing the frontend configuration.

## Python tooling

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from the repository root:

    uv sync --locked

The project uses Python 3.14, selected by `.python-version`. uv creates the local `.venv` and manages the Python environment. The Azure sync tool uses `azure-storage-blob`, `python-dotenv`, and Pillow, managed through uv.

Use `uv add <package>` to add a dependency or `uv add --dev <package>` for a development tool. Commit both `pyproject.toml` and `uv.lock` when dependencies change. Run Python commands through `uv run`; no manual environment activation is needed.

## Run locally

    uv run python -m http.server 8000   # then open http://localhost:8000

## Privacy note

This site shows employee names, photos, titles, hire dates and veteran status. **GitHub Pages sites are public** unless the org is on GitHub Enterprise Cloud, which can restrict Pages to org members. `noindex` is set, but that only keeps the site out of search results; it doesn't stop anyone with the link from viewing it. Before sharing the URL, confirm with HR that public hosting is acceptable.
