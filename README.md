# LinkMint

LinkMint turns a long, difficult-to-share web address into a short and clean link.
Paste a URL, click **Shorten link**, and LinkMint gives you a smaller link that is
easy to copy and share. No account is required.

**Live site:** [linkmint-url-shortener.onrender.com](https://linkmint-url-shortener.onrender.com/)

## The two user journeys

### 1. Creating a short URL

- The user pastes a long URL into LinkMint.
- The browser sends it to the LinkMint app on Render.
- LinkMint checks the URL and creates a unique short code.
- The short code and original URL are saved in the Neon database.
- The new short URL is returned to the user, ready to copy and share.

[View the animated creation journey](docs/diagrams/short-url-creation-flow.svg)

### 2. Opening a short URL

- Someone opens a LinkMint short URL in any browser.
- The request reaches the LinkMint app on Render.
- LinkMint asks the Neon database which original URL belongs to the short code.
- The saved URL is returned to LinkMint.
- The browser is sent to the original website.

[View the animated redirect journey](docs/diagrams/short-url-redirect-flow.svg)

## Where each part runs

- **Browser:** Shows the page and lets users create or open short links.
- **Render:** Runs the website, link-creation API, and redirect logic.
- **Neon:** Stores every short code together with its original URL.
- **GitHub:** Stores the project code and starts a new Render build after changes reach `main`.

## Project structure

```text
MyURLShortener/
|-- app/             Main website and URL-shortening code
|-- migrations/      Saved database changes
|-- scripts/         Small project helper scripts
|-- tests/           Automatic checks
|-- docs/            Source diagrams and project notes
|-- dist/            Ready-to-host copy of the frontend
|-- .github/         GitHub automation
|-- .openai/         Optional ChatGPT Sites project information
|-- project files    Setup, deployment, and package settings
```

### `app/` — the main application

- `__init__.py` — Marks `app` as a Python package.
- `main.py` — Starts LinkMint, serves the webpage, creates links, and handles redirects.
- `config.py` — Reads settings such as the database address and public site URL.
- `database.py` — Opens and manages database connections.
- `models.py` — Describes how a saved link looks in the database.
- `schemas.py` — Describes the information accepted and returned by the API.
- `repository.py` — Saves links and finds them again.
- `service.py` — Creates unique short codes and handles link-creation rules.
- `rate_limit.py` — Prevents one visitor from creating too many links too quickly.

### `app/templates/` — webpage layout

- `index.html` — The structure and text of the LinkMint homepage.

### `app/static/` — webpage design and behaviour

- `styles.css` — Colours, spacing, mobile layout, and visual styling.
- `app.js` — Form submission, copy action, and expandable journey diagrams.
- `favicon.svg` — Small LinkMint icon shown in browser tabs.
- `og.png` — Preview image used when the site is shared on social platforms.
- `diagrams/short-url-creation-flow.svg` — Animated link-creation journey shown on the site.
- `diagrams/short-url-redirect-flow.svg` — Animated redirect journey shown on the site.

### `migrations/` — database change history

- `env.py` — Connects the database-change tool to the project settings.
- `script.py.mako` — Template used when creating a new database change file.
- `versions/20260903_0001_create_links.py` — Creates the `links` table used by LinkMint.

### `scripts/` — helper scripts

- `build_frontend.py` — Creates the ready-to-host frontend inside `dist/`.

### `tests/` — automatic checks

- `conftest.py` — Prepares a safe test app and test database.
- `test_api.py` — Checks link creation, redirects, limits, health pages, and API docs.
- `test_config.py` — Checks that project settings are accepted or rejected correctly.

### `docs/` — project diagrams

- `diagrams/short-url-creation-flow.svg` — Source copy of the creation journey diagram.
- `diagrams/short-url-redirect-flow.svg` — Source copy of the redirect journey diagram.

### `dist/` — built frontend

- `index.html` — Ready-to-host homepage created by the build script.
- `assets/app.js` — Built copy of the browser behaviour.
- `assets/styles.css` — Built copy of the webpage styling.
- `assets/favicon.svg` — Built browser icon.
- `assets/og.png` — Built social sharing image.
- `assets/diagrams/` — Built copies of both animated journey diagrams.

Files in `dist/` are generated from `app/`. Make changes inside `app/`, then run the
build script instead of editing `dist/` by hand.

### `.github/` — GitHub automation

- `workflows/ci.yml` — Runs tests and other checks whenever code is pushed or reviewed.

### `.openai/` — optional site information

- `hosting.json` — Stores optional ChatGPT Sites project information. The live LinkMint
  site currently uses Render, so ChatGPT Sites is not required.

### Files in the project root

- `.env.example` — Example settings for running LinkMint locally.
- `.gitignore` — Keeps passwords, local environments, and temporary files out of GitHub.
- `alembic.ini` — Settings for applying database changes.
- `docker-compose.yml` — Starts a local PostgreSQL database with Docker.
- `pyproject.toml` — Lists the Python version, required packages, and test settings.
- `render.yaml` — Tells Render how to build and start LinkMint.
- `README.md` — This project guide.

Folders such as `.venv`, cache folders, `__pycache__`, and `*.egg-info` are created
automatically on a developer's computer and are not part of the application design.

## Run LinkMint locally

You need Python 3.12 and access to a PostgreSQL database. Docker Desktop is
optional—it is only a quick way to start PostgreSQL on your computer.

First, prepare the project:

```powershell
cd MyURLShortener
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Choose one database option:

- **With Docker:** Run the following command. The database details already present in
  `.env.example` will work with it.

```powershell
docker compose up -d postgres
```

- **Without Docker:** Create your own free Neon database, or install PostgreSQL
  directly on your computer. Put that database connection address after
  `DATABASE_URL=` inside `.env`.

Once the database is ready, start LinkMint:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Then open:

- Website: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API guide: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Keep `.env` private because it can contain a database password.

## Run the checks

```powershell
pytest
ruff check app tests migrations scripts
ruff format --check app tests migrations scripts
```

## Free deployment used by this project

- **GitHub** stores the code.
- **Render's free web service** runs the frontend and backend together.
- **Neon's free PostgreSQL plan** stores the links.
- Pushing to the GitHub `main` branch starts a Render deployment automatically.

Free services may pause after inactivity and can take a little longer to answer the
first request. They also have usage limits, but they are suitable for this project and
portfolio demonstrations.

