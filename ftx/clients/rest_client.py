import hmac
import time
from typing import Optional, Dict, List, Any
from datetime import datetime
from urllib import parse
from requests import Request, Session, Response

class ApiError(Exception):
    pass

class AuthError(ApiError):
    pass

class FtxAuth(object):

    def __init__(self, key: str = '', secret: str = '', subaccount: str = None) -> None:
        self._key = key
        self._secret = secret
        self._subaccount = subaccount

    def get_signature(self, request:Request, ts:int) -> str:
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        return hmac.new(self._secret.encode(), signature_payload, 'sha256').hexdigest()
        
    def sign(self, request: Request) -> None:
        ts = int(time.time() * 1000)
        signature = self.get_signature(request, ts)

        request.headers['FTX-KEY'] = self._key
        request.headers['FTX-SIGN'] = signature
        request.headers['FTX-TS'] = str(ts)
        if self._subaccount:
            request.headers['FTX-SUBACCOUNT'] = parse.quote(self._subaccount)

    def __repr__(self) -> str:
        return f'key:{self._key} secret:{self._secret} {self._subaccount}'


class FtxClient(object):
    _ROOT = 'https://ftx.com/api/'

    def __init__(self, auth: FtxAuth = FtxAuth()) -> None:
        self._session = Session()
        self.auth = auth

    @property
    def auth(self):
        return self._auth

    @auth.setter
    def auth(self, auth):
        if not isinstance(auth, FtxAuth):
            raise ValueError(f'auth is not {FtxAuth} type: {type(auth)}')
        self._auth = auth

    def _request(self, method: str, endpoint: str, **kwargs) -> Response:
        req = Request(method, f'{self._ROOT}{endpoint}', **kwargs)
        self._auth.sign(req)
        return self._session.send(req.prepare())

    def _response(self, response: Response) -> Dict:
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
        else:
            if not data['success']:
                if data['error'] == 'Not logged in':
                    raise AuthError(f'Auth error with {self.auth}')
                else:
                    raise ApiError(data['error'])
            return data['result']

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._response(self._request('GET', endpoint, params=params))

    @staticmethod
    def _paginate(method, *args, **kwargs):
        # Some api methods don't support the limit parameter despite requiring pagination in order to get all the data
        # These methods will use a default limit of 100 (Unreliable) so set this as the default limit check
        # Recommend avoiding to pass the 'limit' argument and use the default in all cases.
        limit = kwargs.get('limit') or 100
        ids = set()
        results = []
        while True:
            response = method(*args, **kwargs)
            deduped_fills = [r for r in response if r['id'] not in ids]
            results.extend(deduped_fills)
            ids |= {d['id'] for d in deduped_fills}
            if len(response) == 0:
                break

            # Fills with identical timestamps might get skipped when setting 'end_time'
            # Must reiterate over smallest timestamp entries -> use a slightly larger 'end_time'
            kwargs['end_time'] = min(datetime.fromisoformat(t['time']) for t in response).timestamp() + 1.0
            if len(response) < limit:
                break

            # Rate limit 30 requests/second
            time.sleep(5e-2)
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
        return self._paginate(self.get_fills, market=market, start_time=start_time, end_time=end_time, limit=100)

    def get_all_funding_payments(self, future: str = None, start_time: float = None, end_time: float = None) -> List[Dict]:
        return self._paginate(self.get_funding_payments, future=future, start_time=start_time, end_time=end_time)
