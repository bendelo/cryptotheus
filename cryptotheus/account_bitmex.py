from hashlib import sha256
from hmac import new
from os import getenv
from threading import Thread
from time import sleep, time

from requests import request

from cryptotheus.context import AccountType, UnitType, CryptotheusContext


class BitmexAccount(Thread):
    __SATOSHI = 0.00000001
    __LABEL_COLLATERAL = 'collateral'

    def __init__(self, context,
                 endpoint=getenv('bitmex_endpoint', 'https://www.bitmex.com'),
                 interval=getenv('bitmex_interval', 30),
                 key=getenv('bitmex_apikey', None),
                 secret=getenv('bitmex_secret', None)
                 ):
        super(BitmexAccount, self).__init__()
        self.__site = 'bitmex'
        self.__balances = {
            'XBt': UnitType.BTC,
        }
        self.__log = context.get_logger(self)
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval
        self.__key = key
        self.__secret = secret

    def run(self):

        while self.__context.is_active():

            threads = [
                Thread(daemon=True, target=self._fetch_collateral),
            ]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            sleep(self.__interval)

    def _json_get(self, path, method='GET', body=''):

        if self.__key is None:
            return None

        if self.__secret is None:
            return None

        timestamp = str(int(time() * 1000))

        data = method + path + timestamp + body

        digest = new(str.encode(self.__secret), str.encode(data), sha256).hexdigest()

        headers = {
            "api-key": self.__key,
            "api-nonce": timestamp,
            "api-signature": digest,
            "Accept": "application/json"
        }

        return request('GET', self.__endpoint + path, headers=headers).json()

    def _fetch_collateral(self):

        json = {}

        try:

            json = self._json_get('/api/v1/user/margin?currency=all')

        except Exception as e:

            self.__log.debug('Collateral Failure : %s - %s', type(e), e.args)

        for ccy, unit in self.__balances.items():

            val = None
            upl = None
            exc = None

            for asset in json if json is not None else []:

                if 'currency' not in asset:
                    continue

                if ccy != asset['currency']:
                    continue

                val = (asset['amount'] * self.__SATOSHI) if 'amount' in asset else None
                upl = (asset['unrealisedPnl'] * self.__SATOSHI) if 'unrealisedPnl' in asset else None
                exc = (asset['excessMargin'] * self.__SATOSHI) if 'excessMargin' in asset else None

            g = self.__context.get_account_gauges(self.__site, AccountType.COLLATERAL, unit)
            g.update_value('deposited', ccy, val)
            g.update_value('unrealized', ccy, upl)
            g.update_value('excess', ccy, exc)
            self.__log.debug('Collateral : deposited = %s, unrealized = %s, excess = %s', val, upl, exc)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = BitmexAccount(context)
    target.start()


if __name__ == '__main__':
    main()
