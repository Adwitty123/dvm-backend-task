# Part B — Last.fm Explorer & Music Passport

A Django application for browsing country charts, searching Last.fm's catalogue, and exploring musical connections between countries. Every upstream request explicitly includes `format=json`; the app never parses XML.

## Setup

Install the shared repository requirements in a virtual environment. Obtain a Last.fm API key from <https://www.last.fm/api/account/create>.

From the repository root:

```bash
cp task_2_music/.env.example task_2_music/.env
```

Set the following value in `task_2_music/.env`:

```dotenv
LASTFM_API_KEY=your_api_key_here
```

Then run:

```bash
python task_2_music/manage.py migrate
python task_2_music/manage.py runserver 8001
```

Open <http://127.0.0.1:8001/>. No Last.fm user password, session token, or API shared secret is required for the public read methods used here. The API key stays on the server. With no key configured, forms load normally and submissions display a configuration message.

## Country charts

Choose a country and either **Top artists** or **Top tracks**, then select **Explore charts**. Each page contains up to 20 entries, with links to their Last.fm pages. Previous/next navigation follows the provider's pagination metadata.

Country choices come from ISO 3166-1 names through `pycountry`, matching the Last.fm country parameter's documented standard. Last.fm may have no results or inconsistent support for some territories; provider errors are shown instead of invented data.

## Catalogue search

Choose **Search**, enter at least two characters, and select **Artists**, **Albums**, or **Tracks**. Results show the name and artist where available. Search pages also contain up to 20 entries.

## Creative additional feature: Music Passport

Music Passport turns country charts into a small musical journey. Instead of manually comparing lists, choose a home country and a destination to receive:

- Shared artists and tracks that connect the two chart samples.
- Destination artists absent from the home sample.
- Separate artist and track overlap percentages.
- A discovery list of up to ten destination tracks absent from the home sample, preserving destination chart order.
- A downloadable JSON passport containing the comparisons, home-only entries, and discovery list.

### Try it

1. Choose **Music Passport** in the navigation.
2. Select **India** as the home country and **Japan** as the destination.
3. Select **Build my passport**.
4. Explore shared favourites and artists to discover.
5. Open discovery tracks on Last.fm.
6. Select **Download passport JSON** to save the complete report.

The feature makes four API requests on a cold cache: artist charts for both countries and track charts for both countries. Each request fetches page 1 with a limit of 20. Warm requests reuse the five-minute cache.

### Comparison method

For each artist or track, names are Unicode NFKC-normalized, trimmed, and case-folded. Track identity includes the artist, so different artists' songs with the same title remain distinct. Duplicate identities count once. The comparison does not use fuzzy matching; alternate spellings, remasters, and collaborations can remain separate.

The displayed percentage is Jaccard similarity:

`overlap = 100 × unique shared entries / unique entries across both samples`

For home entries `{A, B}` and destination entries `{B, C, D}`, the intersection has one entry and the union has four, giving **25%**. Two empty samples display 0%, with empty result messages.

“Discovery” means absent from the home top-20 sample, not unknown in the home country. The output reflects Last.fm's chart samples, not all listeners or national culture. The list links to Last.fm; it does not play audio or create a playlist in an external streaming account. No OAuth, personal listening history, or persistent user profile is needed.

## HTML and JSON endpoints

The same routes render HTML by default and return JSON with `format=json`.

| Route | Required parameters | Optional parameters |
| --- | --- | --- |
| `/` | `country`, `kind=artists` or `kind=tracks` | `page` (1–1000), `format=json` |
| `/search/` | `q`, `kind=artist`, `album`, or `track` | `page` (1–1000), `format=json` |
| `/passport/` | `home`, `destination` (different countries) | `format=json`, `download=1` |

Visiting a route without query parameters displays its blank/default form. Providing `format=json` alone is a validation error because required input parameters are missing. Methods other than GET are rejected.

```bash
curl "http://127.0.0.1:8001/?country=India&kind=artists&format=json"
curl "http://127.0.0.1:8001/?country=Japan&kind=tracks&page=2&format=json"
curl "http://127.0.0.1:8001/search/?q=Radiohead&kind=artist&format=json"
curl "http://127.0.0.1:8001/search/?q=In%20Rainbows&kind=album&format=json"
curl "http://127.0.0.1:8001/search/?q=Weird%20Fishes&kind=track&format=json"
curl "http://127.0.0.1:8001/passport/?home=India&destination=Japan&format=json"
```

A normalized listing response has this structure; the values below are illustrative:

```json
{
  "items": [{"name": "Example song", "artist": "Example artist", "url": "", "kind": "track"}],
  "page": 1,
  "has_next": false,
  "total": 1
}
```

The passport response contains `home`, `destination`, `sample_limit`, `artists`, `tracks`, and `discovery_playlist`. Each comparison contains `overlap_percent`, `shared_count`, `home_count`, `destination_count`, `shared`, `discoveries`, and `home_only`.

## Reliability and security

- The API endpoint is fixed to Last.fm over HTTPS.
- Requests use separate connection and read timeouts of 3.05 and 10 seconds.
- HTTP failures, JSON decoding failures, malformed collections, and Last.fm error objects are handled.
- Upstream success payloads are cached for 300 seconds, keyed by a hash of request parameters. Transport/API error responses are not cached.
- Missing or invalid keys and provider rate limiting return 503; timeouts return 504; other upstream failures return 502; local form errors return 400.
- JSON errors include a readable `error` and structured form errors in `fields`.
- Raw exception URLs and API keys are not echoed to users.
- Templates escape text, and external result links are restricted to HTTP(S) URLs on Last.fm hosts.
- Search length, country values, result types, and page numbers are validated before any API request.

The default in-memory cache is process-local and clears on restart. Use a shared cache and deployment-level request throttling for a public multi-worker deployment. API calls are synchronous and sequential, so a cold passport request can take longer than one chart lookup. Partial passports are not returned when an upstream call fails. There are no automatic retries, background workers, or stale-data fallbacks.

## Architecture

`forms.py` validates user input. `views.py` chooses HTML or JSON output. `services.py` owns Last.fm transport, response normalization, cache access, and passport calculations. Templates provide accessible forms, empty/error states, navigation, and result links. Part B has no custom database models; migrations initialize Django's standard admin/auth/session tables.

## Tests

```bash
python task_2_music/manage.py test music
```

Tests use mocked requests and need no live key. They verify both chart methods, all three search types, JSON request parameters, caching, missing keys, HTTP 429, timeouts, connection failures, invalid JSON, provider errors, malformed payloads, normalization, safe links, overlap mathematics, duplicate identities, discovery ordering, playlist limits, input validation, response status codes, and JSON downloads.

## Last.fm methods

- [`geo.getTopArtists`](https://www.last.fm/api/show/geo.getTopArtists)
- [`geo.getTopTracks`](https://www.last.fm/api/show/geo.getTopTracks)
- [`artist.search`](https://www.last.fm/api/show/artist.search)
- [`album.search`](https://www.last.fm/api/show/album.search)
- [`track.search`](https://www.last.fm/api/show/track.search)

Data is attributed to Last.fm in the page footer. Review [Last.fm's API terms](https://www.last.fm/api/tos) before deploying a public service.
