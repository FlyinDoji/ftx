import time
from urllib import parse
from unittest import TestCase
from unittest.mock import patch
from requests import Request, Session, Response, HTTPError
from ftx.clients.rest_client import FtxAuth, FtxClient, AuthError, ApiError


class FtxAuthTestCase(TestCase):

    def setUp(self):
        self.key = 'api-key'
        self.secret = 'api-secret'
        self.subaccount = 'test subaccount'
        self.url = 'https://test-url.com/api/'
        self.endpoint = 'test-endpoint'
        self.timestamp = 1607195350.5327864
        self.timestamp_ms = 1607195350532
        self.request = Request('GET', f'{self.url}{self.endpoint}')
        self.prepared = self.request.prepare()
    
    @patch('time.time')
    def test_auth_get_signature(self, mocked_timestamp):
        mocked_timestamp.return_value = self.timestamp
        expected_signature = "1d278131ecc4284904dc8afd1d0fae9f2d056a64fac0450300f9439c3cd8821f"
        expected_timestamp = str(self.timestamp_ms)
        
        auth = FtxAuth(self.key,self.secret)
        payload = f'{self.prepared.method}{self.prepared.path_url}'.encode()
        timestamp, signature = auth.get_signature(payload)
        
        self.assertEqual(timestamp, expected_timestamp)
        self.assertEqual(signature, expected_signature)

    @patch('time.time')
    def test_auth_sign(self, mocked_timestamp):
        mocked_timestamp.return_value = self.timestamp
        expected_signature = "1d278131ecc4284904dc8afd1d0fae9f2d056a64fac0450300f9439c3cd8821f"
        expected_timestamp = str(self.timestamp_ms)

        auth = FtxAuth(self.key, self.secret, self.subaccount)
        signed = auth.sign_http_request(self.request)

        self.assertEqual(signed.headers['FTX-KEY'], self.key)
        self.assertEqual(signed.headers['FTX-SIGN'], expected_signature)
        self.assertEqual(signed.headers['FTX-SUBACCOUNT'], parse.quote(self.subaccount))
        self.assertEqual(signed.headers['FTX-TS'], expected_timestamp)


class FtxClientTestCase(TestCase):

    @patch.object(Session, 'send')
    def test_client__request(self, mock_session):
        mock_session.return_value.status_code = 200
        client = FtxClient()
        self.assertEqual(client._request('GET', '/', params={}).status_code, 200)

    # Test exception raising from response with bad code
    def test_client__response_HTTPError(self):
        response = Response()
        response.status_code = 400
        client = FtxClient()
        self.assertRaises(HTTPError, client._response, response=response)

    # Test exception raising from authentication error
    @patch.object(Response, 'json')
    def test_client__response_AuthError(self, mock_response_json):
        mock_response_json.return_value = {'success': None, 'error': 'Not logged in'}
        response = Response()
        response.status_code = 400
        client = FtxClient()
        self.assertRaises(AuthError, client._response, response=response)

    # Test exception raising from api error
    @patch.object(Response, 'json')
    def test_client__response_ApiError(self, mock_response_json):
        mock_response_json.return_value = {'success': None, 'error': 'Anything else'}
        client = FtxClient()
        response = Response()
        response.status_code = 400
        self.assertRaises(ApiError, client._response, response=response)

    @patch.object(Response, 'json')
    def test_client__response(self, mock_response_json):
        mock_response_json.return_value = {'success': True, 'result': 'data'}
        response = Response()
        response.status_code = 200
        client = FtxClient()
        self.assertEqual(client._response(response), 'data')

    # FtxClient._get() is only a wrapper
    @patch.object(FtxClient, '_request')
    def test_client__get(self, mock_client__request):
        mock_client__request.return_value.json = lambda : {'success': True, 'result': 'data'}
        client = FtxClient()
        self.assertEqual(client._get('/'), 'data')
