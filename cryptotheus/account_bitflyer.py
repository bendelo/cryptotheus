from hashlib import sha256
from hmac import new
from logging import DEBUG
from os import getenv
from threading import Thread
from time import sleep, time

from requests import request

from cryptotheus.context import AccountType, UnitType, CryptotheusContext


class BitflyerAccount(Thread):
    __SITE = 'bitflyer'
    __ENDPOINT = getenv(__SITE + '_endpoint', 'https://api.bitflyer.jp')
    __INTERVAL = getenv(__SITE + '_interval', 30)
    __APIKEY = getenv(__SITE + '_apikey', None)
    __SECRET = getenv(__SITE + '_secret', None)
    __BALANCES = {
        'JPY': UnitType.JPY,
        'BTC': UnitType.BTC,
        'ETH': UnitType.ETH,
        'BCH': UnitType.BCH,
    }

    def __init__(self, context, endpoint=__ENDPOINT, interval=__INTERVAL, key=__APIKEY, secret=__SECRET):
        super(BitflyerAccount, self).__init__()
        self.__site = self.__SITE
        self.__balances = self.__BALANCES
        self.__log = context.get_logger(self)
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval
        self.__key = key
        self.__secret = secret

    def run(self):

        while self.__context.is_active():

            threads = [
                Thread(daemon=True, target=self._fetch_balance),
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

        timestamp = str(int(time()))

        data = timestamp + method + path + body

        digest = new(str.encode(self.__secret), str.encode(data), sha256).hexdigest()

        headers = {
            "ACCESS-KEY": self.__key,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-SIGN": digest,
            "Content-Type": "application/json"
        }

        return request('GET', self.__endpoint + path, headers=headers).json()

    def _fetch_balance(self):

        json = None

        try:

            json = self._json_get('/v1/me/getbalance')

        except Exception as e:

            self.__log.debug('Balance Failure : %s - %s', type(e), e.args)

        for ccy, unit in self.__balances.items():

            value = None

            for asset in json if json is not None else []:

                if 'currency_code' not in asset:
                    continue

                if ccy != asset['currency_code']:
                    continue

                value = asset['amount'] if 'amount' in asset else None

            g = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, unit)
            g.update_value('cash', ccy, value)
            self.__log.debug('Balance : %s = %s', ccy, value)


def main():
    context = CryptotheusContext(log_level=DEBUG)
    context.launch_server()

    target = BitflyerAccount(context)
    target.start()


if __name__ == '__main__':
    main()
