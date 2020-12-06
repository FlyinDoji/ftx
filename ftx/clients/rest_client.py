import hmac
import time
from datetime import datetime
from urllib import parse
from typing import Dict, List, Tuple, Any
from requests import Request, Session, Response, HTTPError, PreparedRequest

class ApiError(Exception):
    pass

class AuthError(ApiError):
    pass


class FtxAuth(object):

    def __init__(self, key: str = '', secret: str = '', subaccount: str = '') -> None:
        self._key = key
        self._secret = secret
        self._subaccount = subaccount

    # Signs encoded payloads and returns milisecond timestamp and signature
    def get_signature(self, payload:bytes) -> Tuple[str, str]:
        # Timestamp in miliseconds
        timestamp = str(int(time.time() * 1000))
        return timestamp, hmac.new(self._secret.encode(), timestamp.encode() + payload, 'sha256').hexdigest()
    
    # Takes a Request and returns a PreparedRequest with appropriate headers
    def sign_http_request(self, request: Request) -> PreparedRequest:
        prepared = request.prepare()
        http_payload = f'{prepared.method}{prepared.path_url}'.encode()
        # POST requests will have serialized JSON as body, encode payload before appending
        if prepared.body:
            http_payload += prepared.body
        timestamp, signature = self.get_signature(http_payload)
        prepared.headers['FTX-KEY'] = self._key
        prepared.headers['FTX-SIGN'] = signature
        prepared.headers['FTX-TS'] = timestamp
        if self._subaccount:
            prepared.headers['FTX-SUBACCOUNT'] = parse.quote(self._subaccount)
        return prepared

    # Returns a ws authentication message
    def sign_ws_message(self) -> str:
        pass

    def __repr__(self) -> str:
        return f'key:{self._key} secret:{self._secret} {self._subaccount}'


class FtxClient(object):
    _ROOT = 'https://ftx.com/api/'
    # Rate limit 30 requests / second
    _RATELIMIT = 0.035

    def __init__(self, auth: FtxAuth = FtxAuth()) -> None:
        self._session = Session()
        self.auth = auth

    @property
    def auth(self):
        return self._auth

    @auth.setter
    def auth(self, auth:FtxAuth):
        if not isinstance(auth, FtxAuth):
            raise ValueError(f'auth is not {FtxAuth} type: {type(auth)}')
        self._auth = auth

    # Creates and signs a Request to be sent to the server
    def _request(self, method: str, endpoint: str, params:Dict) -> Response:
        req = Request(method, f'{FtxClient._ROOT}{endpoint}', params=params)
        signed = self._auth.sign_http_request(req)
        return self._session.send(signed)

    # Checks Response for errors, raises appropiate error or returns operation results
    def _response(self, response: Response) -> Dict:
        try:
            response.raise_for_status()
        except HTTPError:
            # Check if error message is present, client problem probably
            try:    
                data = response.json()
                if data['error'] == 'Not logged in':
                    raise AuthError(f'Auth error with {self.auth}')
                else:
                    raise ApiError(data['error'])
            # Server did not return any response, server might be busy
            except ValueError:
                raise HTTPError
            
        return response.json()['result']

    # Wrapper for client methods that use GET
    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        return self._response(self._request('GET', endpoint, params=params))

    # Wrapper for pulling more data that can be passed through a single request
    @staticmethod
    def _paginate(method, *args, **kwargs):
        # /funding_payments API call does not use 'limit' despite requiring pagination
        # will error if parameter is sent and defaults to 100 entries being sent at max in a single response
        # /fills API call uses 'limit' but defaults to 20 if parameter is not sent
        limit = kwargs.get('limit') or 100
        ids = set()
        results = []
        while True:
            response = method(*args, **kwargs)
            duplicates_removed = [r for r in response if r['id'] not in ids]
            results.extend(duplicates_removed)
            ids |= {d['id'] for d in duplicates_removed}

            # Fills with identical timestamps might get skipped when setting 'end_time'
            # Must include the largest timestamp again, in case not all fills were included in the response
            kwargs['end_time'] = min(datetime.fromisoformat(t['time']) for t in response).timestamp() + 1.0

            if len(response) < limit:
                break

            time.sleep(FtxClient._RATELIMIT)
        return results

    def list_futures(self) -> List[Dict]:
        return self._get('futures')

    def list_markets(self) -> List[Dict]:
        return self._get('markets')

    def get_account_info(self) -> Dict:
        return self._get('account')

    def get_subaccounts(self) -> List[Dict]:
        return self._get('subaccounts')

    def get_positions(self, show_avg_price: bool = False) -> List[Dict]:
        return self._get('positions', {'showAvgPrice': show_avg_price})

    def get_fills(self, market: str = None, start_time: float = None,
                  end_time: float = None, limit: int = None) -> List[Dict]:
        params = {}
        if market:
            params['market'] = market
        if limit:
            params['limit'] = limit
        if start_time:
            params['start_time'] = int(start_time)
        if end_time:
            params['end_time'] = int(end_time)
        return self._get('fills', params)

    def get_funding_payments(self, future: str = None, start_time: float = None, end_time: float = None) -> List[Dict]:
        params = {}
        if future:
            params['future'] = future
        if start_time:
            params['start_time'] = int(start_time)
        if end_time:
            params['end_time'] = int(end_time)
        return self._get('funding_payments', params)

    def get_all_fills(self, market: str = None, start_time: float = None, end_time: float = None) -> List[Dict]:
        return FtxClient._paginate(self.get_fills, market=market, start_time=start_time, end_time=end_time, limit=100)

    def get_all_funding_payments(self, future: str = None, start_time: float = None, end_time: float = None) -> List[Dict]:
        return FtxClient._paginate(self.get_funding_payments, future=future, start_time=start_time, end_time=end_time)
