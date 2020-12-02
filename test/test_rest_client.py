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
        self.timestamp = 1606765690995
        self.parameters = dict()
        self.request = Request('GET', f'{self.url}{self.endpoint}', self.parameters)
        
    def test_auth_get_signature(self):
        auth = FtxAuth(self.key,self.secret)
        expected_signature = "46aeefae43a28c9c1a1f8fd95614cd0d4867c8d2b0ee3b40c17741173dc84c2b"
        
        self.assertEqual(auth.get_signature(self.request, self.timestamp), expected_signature)

    def test_auth_sign(self):
        auth = FtxAuth(self.key, self.secret, self.subaccount)
        request = self.request
        auth.sign(request)

        self.assertEqual(request.headers['FTX-KEY'], self.key)
        self.assertEqual(request.headers['FTX-SIGN'], auth.get_signature(self.request, request.headers['FTX-TS']))
        self.assertEqual(request.headers['FTX-SUBACCOUNT'], parse.quote(self.subaccount))


class FtxClientTestCase(TestCase):

    @patch.object(Session, 'send')
    def test_client__request(self, mock_session):
        mock_session.return_value.status_code = 200

        client = FtxClient()
        self.assertEqual(client._request('GET', '/').status_code, 200)

    # Test exception raising from response with bad code
    @patch.object(Response, 'json')
    @patch.object(Response, 'raise_for_status')
    def test_client__response_HTTPError(self, mock_response_json, mock_response_raise_for_status):
        mock_response_json.side_effect = ValueError()
        mock_response_raise_for_status.side_effect = HTTPError()
        client = FtxClient()
        self.assertRaises(HTTPError, client._response, response=Response())

    # Test exception raising from authentication error
    @patch.object(Response, 'json')
    def test_client__response_AuthError(self, mock_response_json):
        mock_response_json.return_value = {'success': None, 'error': 'Not logged in'}
        client = FtxClient()
        self.assertRaises(AuthError, client._response, response=Response())

    # Test exception raising from api error
    @patch.object(Response, 'json')
    def test_client__response_ApiError(self, mock_response_json):
        mock_response_json.return_value = {'success': None, 'error': 'Anything else'}
        client = FtxClient()
        self.assertRaises(ApiError, client._response, response=Response())

    @patch.object(Response, 'json')
    def test_client__response(self, mock_response_json):
        data = 'success'
        mock_response_json.return_value = {'success': True, 'result': data}
        client = FtxClient()
        self.assertEqual(client._response(Response()), data)

    # FtxClient._get() is only a wrapper
    @patch.object(FtxClient, '_request')
    def test_client__get(self, mock_client__request):
        mock_client__request.return_value.json = lambda : {'success':True, 'result':'data'}
        client = FtxClient()
        self.assertEqual(client._get('/'), 'data')
