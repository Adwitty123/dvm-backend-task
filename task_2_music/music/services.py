import hashlib
import json
import unicodedata
from urllib.parse import urlparse
import requests
from django.conf import settings
from django.core.cache import cache


class LastFMError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


class LastFMClient:
    endpoint = 'https://ws.audioscrobbler.com/2.0/'

    def request(self, method, **params):
        if not settings.LASTFM_API_KEY:
            raise LastFMError('Add LASTFM_API_KEY to task_2_music/.env and restart the server.', 503)
        params.update(method=method, api_key=settings.LASTFM_API_KEY, format='json')
        key = 'lastfm:' + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            response = requests.get(self.endpoint, params=params, timeout=(3.05, 10))
            if response.status_code == 429:
                raise LastFMError('Last.fm is rate limiting requests. Please try again shortly.', 503)
            response.raise_for_status()
            data = response.json()
        except requests.Timeout as exc:
            raise LastFMError('Last.fm took too long to respond. Please try again.', 504) from exc
        except requests.RequestException as exc:
            raise LastFMError('Last.fm is temporarily unavailable. Please try again later.') from exc
        except ValueError as exc:
            raise LastFMError('Last.fm returned an invalid JSON response.') from exc
        if not isinstance(data, dict):
            raise LastFMError('Last.fm returned an unexpected response.')
        if 'error' in data:
            code = str(data['error'])
            if code in {'10', '26'}:
                raise LastFMError('The Last.fm API key is invalid or suspended. Check your .env file.', 503)
            if code in {'11', '16', '29'}:
                raise LastFMError('Last.fm is temporarily unavailable or rate limiting requests.', 503)
            raise LastFMError('Last.fm could not process this request. Check the country or search terms.')
        cache.set(key, data, settings.LASTFM_CACHE_SECONDS)
        return data

    def charts(self, country, kind, page=1, limit=20):
        if kind not in {'artists', 'tracks'}:
            raise ValueError('Unsupported chart type.')
        singular = 'artist' if kind == 'artists' else 'track'
        data = self.request('geo.getTopArtists' if kind == 'artists' else 'geo.getTopTracks', country=country, page=page, limit=limit)
        section = data.get('topartists' if kind == 'artists' else 'tracks')
        return self.collection(section, singular, page, limit)

    def search(self, query, kind, page=1, limit=20):
        if kind not in {'artist', 'album', 'track'}:
            raise ValueError('Unsupported search type.')
        data = self.request(f'{kind}.search', **{kind: query, 'page': page, 'limit': limit})
        results = data.get('results')
        if not isinstance(results, dict):
            raise LastFMError('Last.fm returned an unexpected search response.')
        matches = results.get(f'{kind}matches', {})
        if not isinstance(matches, dict):
            raise LastFMError('Last.fm returned invalid search matches.')
        items = normalize_items(matches.get(kind, []), kind)
        total = integer(results.get('opensearch:totalResults'), 0)
        return {'items': items, 'page': page, 'has_next': page * limit < total, 'total': total}

    def collection(self, section, kind, page, limit):
        if not isinstance(section, dict):
            raise LastFMError('Last.fm returned an unexpected chart response.')
        items = normalize_items(section.get(kind, []), kind)
        attrs = section.get('@attr', {})
        if not isinstance(attrs, dict):
            attrs = {}
        return {'items': items, 'page': page, 'has_next': page < integer(attrs.get('totalPages'), 1), 'total': integer(attrs.get('total'), len(items))}


def integer(value, default):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def safe_url(value):
    if not isinstance(value, str):
        return ''
    try:
        parsed = urlparse(value)
        if parsed.scheme in {'http', 'https'} and parsed.hostname and (parsed.hostname == 'last.fm' or parsed.hostname.endswith('.last.fm')):
            return value
    except ValueError:
        pass
    return ''


def normalize_items(raw, kind):
    if raw in (None, ''):
        return []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise LastFMError('Last.fm returned an invalid result list.')
    items = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str):
            continue
        artist = item.get('artist', '')
        if isinstance(artist, dict):
            artist = artist.get('name', '')
        items.append({'name': item['name'], 'artist': artist if isinstance(artist, str) else '', 'url': safe_url(item.get('url', '')), 'kind': kind})
    return items


def identity(item):
    return tuple(unicodedata.normalize('NFKC', value).strip().casefold() for value in (item['name'], item.get('artist', '')))


def compare(home_items, destination_items):
    home_map = {identity(item): item for item in home_items}
    destination_map = {identity(item): item for item in destination_items}
    shared_keys = home_map.keys() & destination_map.keys()
    union = home_map.keys() | destination_map.keys()
    return {
        'overlap_percent': round(100 * len(shared_keys) / len(union), 1) if union else 0,
        'shared_count': len(shared_keys),
        'home_count': len(home_map),
        'destination_count': len(destination_map),
        'shared': [item for key, item in destination_map.items() if key in shared_keys],
        'discoveries': [item for key, item in destination_map.items() if key not in home_map],
        'home_only': [item for key, item in home_map.items() if key not in destination_map],
    }


def build_passport(home, destination):
    client = LastFMClient()
    report = {'home': home, 'destination': destination, 'sample_limit': 20}
    for kind in ['artists', 'tracks']:
        home_items = client.charts(home, kind)['items']
        destination_items = client.charts(destination, kind)['items']
        report[kind] = compare(home_items, destination_items)
    report['discovery_playlist'] = report['tracks']['discoveries'][:10]
    return report
