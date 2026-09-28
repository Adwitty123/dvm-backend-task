# DVM Backend Task

Two independent Django projects in one repository, covering the recruitment assignment's Part A and Part B. Python source, templates, styles, migrations, and configuration contain no code comments.

| Folder | Project | Additional feature |
| --- | --- | --- |
| [`task_1_polls`](task_1_polls/README.md) | Django tutorial polls application | Community-created polls with accounts, closing dates, one vote per account, and pagination |
| [`task_2_music`](task_2_music/README.md) | Last.fm country charts and catalogue search | Music Passport: compare two countries and export a discovery list |

## Requirements

- Python 3.10 or newer; Python 3.12 is recommended and used by CI.
- pip and a virtual environment.
- A Last.fm API key for Part B's live data. Part A and all automated tests work without one.
- SQLite is included with Python. The projects use separate databases.

## Quick start

Run these commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

### Part A

```bash
cp task_1_polls/.env.example task_1_polls/.env
python task_1_polls/manage.py migrate
python task_1_polls/manage.py seed_polls
python task_1_polls/manage.py createsuperuser
python task_1_polls/manage.py runserver 8000
```

Open <http://127.0.0.1:8000/>. Sign up through the site to create polls and vote. The superuser is for the admin interface and is optional for normal use.

### Part B

In another terminal, activate the same environment:

```bash
cp task_2_music/.env.example task_2_music/.env
python task_2_music/manage.py migrate
python task_2_music/manage.py runserver 8001
```

Before starting the server, set `LASTFM_API_KEY` in `task_2_music/.env`. Obtain a key at <https://www.last.fm/api/account/create>. Open <http://127.0.0.1:8001/>.

Windows users can replace `cp` with `Copy-Item`.

## Test both projects

```bash
python task_1_polls/manage.py test polls
python task_2_music/manage.py test music
python task_1_polls/manage.py check
python task_2_music/manage.py check
python task_1_polls/manage.py makemigrations --check --dry-run
```

The music tests mock external calls; no API key or network connection is needed. Tests cover permissions, CSRF, duplicate votes, poll validation, future/closed polls, pagination, Last.fm request parameters, caching, invalid JSON, timeouts, provider errors, search types, comparison mathematics, and JSON downloads.

GitHub Actions runs both projects independently on every push and pull request. See [`.github/workflows/tests.yml`](.github/workflows/tests.yml).

## Repository layout

| Path | Purpose |
| --- | --- |
| `requirements.txt` | Shared compatible dependency ranges |
| `requirements-lock.txt` | Exact dependency versions used for local verification |
| `task_1_polls/config/` | Polls project settings, URLs, and WSGI entry point |
| `task_1_polls/polls/` | Models, views, forms, admin, migrations, tests, and seed command |
| `task_1_polls/templates/` | Poll and authentication pages |
| `task_2_music/config/` | Music project settings, URLs, and WSGI entry point |
| `task_2_music/music/services.py` | Last.fm HTTP client, normalization, and comparison logic |
| `task_2_music/music/forms.py` | Country, search, and comparison validation |
| `task_2_music/music/views.py` | HTML and JSON views |
| `task_2_music/templates/` | Chart, search, and passport pages |

Each project has its own `manage.py`, `.env.example`, static stylesheet, and detailed README.

## Publish to one GitHub repository

Create an empty GitHub repository, then run from this repository's root, replacing the URL with your own:

```bash
git add .
git commit -m "Complete DVM backend tasks"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/dvm-backend-task.git
git push -u origin main
```

If you extracted the ZIP and Git reports that this is not a repository, run `git init` first. If the delivered local repository already has its initial commit, skip the commit command when there is nothing to commit. Never commit `.env`, API keys, or local databases; these are ignored.

## Configuration and deployment notes

Both projects default to local development with `DJANGO_DEBUG=true`. `.env` files are loaded automatically and do not override existing process environment variables. Set a unique, strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and explicit `DJANGO_ALLOWED_HOSTS` before deployment. A missing secret in non-debug mode fails at startup. Debug Toolbar is development-only and limited to local IPs.

For a real deployment, configure HTTPS, a production WSGI server, static-file serving after `collectstatic`, persistent database storage, and shared caching as needed. Run `python manage.py check --deploy` within each project and address deployment-specific settings. The Django development server is for local use. Authentication and CSRF protection are included; public registration and expensive external API endpoints would also need deployment-level abuse prevention.

## References

- [Django tutorial, parts 1–8](https://docs.djangoproject.com/en/5.2/intro/tutorial01/)
- [Django testing tutorial](https://docs.djangoproject.com/en/5.2/intro/tutorial05/)
- [Django Debug Toolbar installation](https://django-debug-toolbar.readthedocs.io/en/latest/installation.html)
- [Last.fm API documentation](https://www.last.fm/api)

See each task's README for feature walkthroughs, implementation decisions, and limitations.
