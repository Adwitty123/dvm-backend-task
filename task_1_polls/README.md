# Part A — Community Polls

A Django tutorial-style polling application with questions, choices, results, an admin interface, static styling, automated tests, and Django Debug Toolbar. The reusable-app packaging tutorial is intentionally outside the assignment scope.

## Setup

Requires Python 3.12 or newer and Django 6.1. The shared lock file pins Django 6.1.1.

From the repository root, install the shared requirements in an activated virtual environment, then run:

```bash
cp task_1_polls/.env.example task_1_polls/.env
python task_1_polls/manage.py migrate
python task_1_polls/manage.py seed_polls
python task_1_polls/manage.py createsuperuser
python task_1_polls/manage.py runserver 8000
```

Visit <http://127.0.0.1:8000/>. The optional seed command is safe to run more than once and creates two sample polls without default accounts or passwords.

## Additional feature: community-created, time-limited polls

Users can publish polls directly through the website. Each poll has an author, 2–8 distinct choices, and a closing time. Voting requires an account, and each account can vote once per poll.

### Walkthrough

1. Choose **Sign up**, enter a username and a password, and submit. You are logged in automatically.
2. Choose **Create a poll**.
3. Enter a question of up to 200 characters.
4. Enter 2–8 choices, one per line. Choices must be unique ignoring letter case and contain no more than 200 characters each.
5. Choose a duration of 1, 3, 7, or 30 days and select **Publish poll**.
6. Share the resulting poll URL. Other users can register or log in and cast one vote each.
7. Choose **View results** to see counts, percentages, and progress bars.
8. After the closing time, results remain visible but new votes are rejected. Dates on the page use UTC.

Polls are listed newest first, ten per page. Scheduled future polls created in the admin are hidden from the list, detail page, results page, and voting endpoint until publication.

## Routes

| Method | Route | Behaviour |
| --- | --- | --- |
| GET | `/` | Paginated published polls; optional `?page=2` |
| GET, POST | `/polls/create/` | Authenticated poll creation |
| GET | `/polls/<id>/` | Poll details and voting form |
| POST | `/polls/<id>/vote/` | Authenticated, CSRF-protected vote |
| GET | `/polls/<id>/results/` | Counts and percentages |
| GET, POST | `/accounts/signup/` | Registration |
| GET, POST | `/accounts/login/` | Login |
| POST | `/accounts/logout/` | Logout |
| GET, POST | `/admin/` | Staff administration |

## Tutorial coverage

| Tutorial area | Implementation |
| --- | --- |
| Project, app, URL routing, views | `config/`, `polls/urls.py`, `polls/views.py` |
| Models, database, migrations | `Question`, `Choice`, `Vote`, committed initial migration |
| Admin customization | Inline choices, search, date filters, recent-publication display |
| Templates and forms | Namespaced routes, inherited templates, validated forms, CSRF |
| Generic views | `ListView` and `DetailView` for index, detail, and results |
| Automated tests | Model boundaries, visibility, permissions, validation, voting, results |
| Static files | App stylesheet loaded through Django static handling |
| Debug Toolbar | Development middleware, URLs, local IPs, complete HTML documents |

## Voting integrity

The `Vote` table has a database uniqueness constraint on `(user, question)`. Creating a vote and incrementing the choice counter happen in one transaction. The counter uses an `F()` expression to avoid read-modify-write lost updates. Replaying a vote request produces a friendly message and does not increment the counter again.

The view resolves a submitted choice through the current question's related choices, so a choice from another poll cannot be submitted. GET requests cannot cast votes, and CSRF checks protect POST requests. Poll creation is also transactional, so the question and its choices are saved together.

`Choice.votes` preserves the tutorial's aggregate counter. Vote records enforce one vote per existing account. Administrative deletion of accounts or choices is not a vote-retraction workflow, and direct database edits are outside these application guarantees. The application does not offer vote changes or vote retraction. Multiple accounts can still vote; this is not an identity-verification system.

## Use Django Debug Toolbar

1. Keep `DJANGO_DEBUG=true` in `.env`.
2. Start the server and use `http://127.0.0.1:8000/` locally.
3. Open the toolbar on the right side of an HTML page.
4. Inspect **SQL** to see database queries, **Templates** to see template/context information, and **Timer** to inspect request timing.
5. Browse an index page and a poll detail page to compare the queries. The index uses `select_related('author')`; details prefetch choices.

The toolbar is not loaded by the normal `manage.py test` command and is not enabled with `DJANGO_DEBUG=false`. It is intended for loopback access, not remote visitors. If it does not appear, check DEBUG, the local address, static files, and the browser's HTML page response.

## Tests

```bash
python task_1_polls/manage.py test polls
```

Tests include future, old, and recent publication; empty index; pagination; hidden future details and results; anonymous access; repeated votes; invalid and foreign choices; expired polls; CSRF; database uniqueness; creation; invalid choices; zero-vote results; and signup. Django creates and removes a separate test database.
