from unittest.mock import Mock, patch
import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from .services import LastFMClient, LastFMError, build_passport, compare, normalize_items, safe_url


def item(name, artist=''):
    return {'name': name, 'artist': artist, 'url': '', 'kind': 'track'}


@override_settings(LASTFM_API_KEY='test-key', LASTFM_CACHE_SECONDS=300)
class ClientTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client_api = LastFMClient()

    @patch('music.services.requests.get')
    def test_json_parameters_timeout_and_cache(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'topartists': {'artist': [{'name': 'Artist'}], '@attr': {'totalPages': '2', 'total': '30'}}}
        for _ in range(2):
            result = self.client_api.charts('India', 'artists')
            self.assertEqual(result['items'][0]['name'], 'Artist')
            self.assertTrue(result['has_next'])
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs['params']['format'], 'json')
        self.assertEqual(get.call_args.kwargs['params']['method'], 'geo.getTopArtists')
        self.assertEqual(get.call_args.kwargs['timeout'], (3.05, 10))

    @patch('music.services.requests.get')
    def test_track_chart_nested_artist(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'tracks': {'track': [{'name': 'Song', 'artist': {'name': 'Singer'}}]}}
        result = self.client_api.charts('Japan', 'tracks')
        self.assertEqual(result['items'][0]['artist'], 'Singer')
        self.assertEqual(get.call_args.kwargs['params']['method'], 'geo.getTopTracks')

    @patch('music.services.requests.get')
    def test_all_search_types(self, get):
        for kind in ['artist', 'album', 'track']:
            with self.subTest(kind=kind):
                get.return_value = Mock(status_code=200)
                get.return_value.json.return_value = {'results': {f'{kind}matches': {kind: {'name': 'Match', 'artist': 'Singer'}}, 'opensearch:totalResults': '21'}}
                result = self.client_api.search('Match', kind)
                self.assertEqual(result['items'][0]['name'], 'Match')
                self.assertTrue(result['has_next'])
                self.assertEqual(get.call_args.kwargs['params'][kind], 'Match')

    @override_settings(LASTFM_API_KEY='')
    @patch('music.services.requests.get')
    def test_missing_key_never_calls_network(self, get):
        with self.assertRaises(LastFMError) as error:
            self.client_api.charts('India', 'artists')
        self.assertEqual(error.exception.status, 503)
        get.assert_not_called()

    @patch('music.services.requests.get')
    def test_timeout(self, get):
        get.side_effect = requests.Timeout
        with self.assertRaises(LastFMError) as error:
            self.client_api.charts('India', 'artists')
        self.assertEqual(error.exception.status, 504)

    @patch('music.services.requests.get')
    def test_network_error_does_not_leak_key(self, get):
        get.side_effect = requests.ConnectionError('URL contains test-key')
        with self.assertRaises(LastFMError) as error:
            self.client_api.charts('India', 'artists')
        self.assertNotIn('test-key', str(error.exception))

    @patch('music.services.requests.get')
    def test_http_rate_limit(self, get):
        get.return_value = Mock(status_code=429)
        with self.assertRaises(LastFMError) as error:
            self.client_api.charts('India', 'artists')
        self.assertEqual(error.exception.status, 503)

    @patch('music.services.requests.get')
    def test_lastfm_errors_are_not_cached(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'error': 10, 'message': 'Invalid key'}
        for _ in range(2):
            with self.assertRaises(LastFMError):
                self.client_api.charts('India', 'artists')
        self.assertEqual(get.call_count, 2)

    @patch('music.services.requests.get')
    def test_invalid_json(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.side_effect = ValueError('bad JSON')
        with self.assertRaises(LastFMError):
            self.client_api.charts('India', 'artists')

    @patch('music.services.requests.get')
    def test_malformed_payloads(self, get):
        for payload in [[], {}, {'topartists': []}, {'topartists': {'artist': 42}}]:
            cache.clear()
            get.return_value = Mock(status_code=200)
            get.return_value.json.return_value = payload
            with self.subTest(payload=payload), self.assertRaises(LastFMError):
                self.client_api.charts('India', 'artists')


class PassportTests(SimpleTestCase):
    def test_jaccard_overlap_and_discovery_order(self):
        result = compare([item('A'), item('B')], [item('B'), item('C'), item('D')])
        self.assertEqual(result['overlap_percent'], 25)
        self.assertEqual([row['name'] for row in result['discoveries']], ['C', 'D'])
        self.assertEqual(result['shared_count'], 1)

    def test_empty_comparison(self):
        self.assertEqual(compare([], [])['overlap_percent'], 0)

    def test_case_unicode_and_duplicates(self):
        result = compare([item('Ａ'), item('a')], [item(' A ')])
        self.assertEqual(result['overlap_percent'], 100)
        self.assertEqual(result['home_count'], 1)

    def test_same_title_different_artists_are_distinct(self):
        result = compare([item('Hello', 'Adele')], [item('Hello', 'Lionel Richie')])
        self.assertEqual(result['overlap_percent'], 0)

    @patch('music.services.LastFMClient.charts')
    def test_passport_calls_both_charts_and_caps_playlist(self, charts):
        charts.side_effect = [{'items': []}, {'items': []}, {'items': []}, {'items': [item(str(i)) for i in range(15)]}]
        report = build_passport('India', 'Japan')
        self.assertEqual(charts.call_count, 4)
        self.assertEqual(len(report['discovery_playlist']), 10)

    def test_normalization_and_safe_links(self):
        self.assertEqual(normalize_items(None, 'track'), [])
        self.assertEqual(safe_url('javascript:alert(1)'), '')
        self.assertEqual(safe_url('https://last.fm.evil.example/song'), '')
        self.assertEqual(safe_url('https://www.last.fm/music/Test'), 'https://www.last.fm/music/Test')


class ViewTests(SimpleTestCase):
    def test_forms_load_without_api_key(self):
        for url in ['/', '/search/', '/passport/']:
            self.assertEqual(self.client.get(url).status_code, 200)

    @patch('music.views.LastFMClient.charts')
    def test_invalid_country_and_page_do_not_call_api(self, charts):
        for params in [{'country': 'Atlantis', 'kind': 'artists'}, {'country': 'India', 'kind': 'artists', 'page': '-1'}]:
            response = self.client.get('/', {**params, 'format': 'json'})
            self.assertEqual(response.status_code, 400)
        charts.assert_not_called()

    @patch('music.views.LastFMClient.search')
    def test_search_json_and_html(self, search):
        search.return_value = {'items': [item('Found')], 'page': 1, 'total': 1, 'has_next': False}
        params = {'q': 'Found', 'kind': 'track'}
        self.assertContains(self.client.get('/search/', params), 'Found')
        self.assertEqual(self.client.get('/search/', {**params, 'format': 'json'}).json()['items'][0]['name'], 'Found')

    @patch('music.views.LastFMClient.charts')
    def test_api_failure_json_status(self, charts):
        charts.side_effect = LastFMError('Try later', 503)
        response = self.client.get('/', {'country': 'India', 'kind': 'artists', 'format': 'json'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'Try later')

    def test_same_country_rejected(self):
        self.assertEqual(self.client.get('/passport/', {'home': 'India', 'destination': 'India', 'format': 'json'}).status_code, 400)

    @patch('music.views.build_passport')
    def test_download(self, build):
        build.return_value = {'home': 'India', 'destination': 'Japan', 'discovery_playlist': []}
        response = self.client.get('/passport/', {'home': 'India', 'destination': 'Japan', 'download': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="music-passport.json"')
        self.assertEqual(response.json()['destination'], 'Japan')

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post('/search/').status_code, 405)
