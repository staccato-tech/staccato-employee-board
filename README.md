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

    python3 scripts/build_data.py path/to/WordPress-export.xml

This script also cleans up department names. For example, `910 - OPS- Machine Shop` becomes `Machine Shop`, and stray numeric IDs are removed.

### Photos

Photos still point at the old WP Engine media library. To copy them into this repo so the site doesn't depend on WP Engine anymore, run:

    python3 scripts/localize_photos.py

## Run locally

    python3 -m http.server 8000   # then open http://localhost:8000

## Privacy note

This site shows employee names, photos, titles, hire dates and veteran status. **GitHub Pages sites are public** unless the org is on GitHub Enterprise Cloud, which can restrict Pages to org members. `noindex` is set, but that only keeps the site out of search results; it doesn't stop anyone with the link from viewing it. Before sharing the URL, confirm with HR that public hosting is acceptable.
