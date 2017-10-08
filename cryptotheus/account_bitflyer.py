from hashlib import sha256
from hmac import new
from os import getenv
from threading import Thread
from time import sleep, time

from requests import request

from cryptotheus.context import AccountType, UnitType, ProductType, CryptotheusContext


class BitflyerAccount(Thread):
    __LABEL_CASH = 'cash'
    __LABEL_MARGIN = 'cash'

    def __init__(self, context,
                 endpoint=getenv('bitflyer_endpoint', 'https://api.bitflyer.jp'),
                 interval=getenv('bitflyer_interval', 30),
                 key=getenv('bitflyer_apikey', None),
                 secret=getenv('bitflyer_secret', None)
                 ):
        super(BitflyerAccount, self).__init__()
        self.__site = 'bitflyer'
        self.__balances = {
            'JPY': UnitType.JPY,
            'BTC': UnitType.BTC,
            'ETH': UnitType.ETH,
            'BCH': UnitType.BCH,
        }
        self.__collateral = {
            'JPY': UnitType.JPY,
            'BTC': UnitType.BTC,
        }
        self.__margins = {
            'FX_BTC_JPY': UnitType.BTC,
            'BTCJPY_MAT1WK': UnitType.BTC,
            'BTCJPY_MAT2WK': UnitType.BTC,
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
                Thread(daemon=True, target=self._fetch_balance),
                Thread(daemon=True, target=self._fetch_collateral),
                Thread(daemon=True, target=self._fetch_margin),
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
            g.update_value(self.__LABEL_CASH, ccy, value)
            self.__log.debug('Balance : %s = %s', ccy, value)

            if unit == UnitType.BTC:
                btc_ticker = self.__context.get_ticker_gauges(self.__site, ProductType.JPY_BTC)
                btc_price = btc_ticker.get_cached_mid('BTC_JPY')

                jpy = value * btc_price \
                    if value is not None and btc_price is not None \
                    else None

                account = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
                account.update_value(self.__LABEL_CASH, ccy, jpy)

            if unit == UnitType.ETH:
                alt_ticker = self.__context.get_ticker_gauges(self.__site, ProductType.BTC_ETH)
                alt_price = alt_ticker.get_cached_mid('ETH_BTC')
                btc = value * alt_price if value is not None and alt_price is not None else None
                account = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.BTC)
                account.update_value(self.__LABEL_CASH, ccy, btc)

                btc_ticker = self.__context.get_ticker_gauges(self.__site, ProductType.JPY_BTC)
                btc_price = btc_ticker.get_cached_mid('BTC_JPY')
                jpy = btc * btc_price if btc is not None and btc_price is not None else None
                account = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
                account.update_value(self.__LABEL_CASH, ccy, jpy)

            if unit == UnitType.BCH:
                alt_ticker = self.__context.get_ticker_gauges(self.__site, ProductType.BTC_BCH)
                alt_price = alt_ticker.get_cached_mid('BCH_BTC')
                btc = value * alt_price if value is not None and alt_price is not None else None
                account = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.BTC)
                account.update_value(self.__LABEL_CASH, ccy, btc)

                btc_ticker = self.__context.get_ticker_gauges(self.__site, ProductType.JPY_BTC)
                btc_price = btc_ticker.get_cached_mid('BTC_JPY')
                jpy = btc * btc_price if btc is not None and btc_price is not None else None
                account = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
                account.update_value(self.__LABEL_CASH, ccy, jpy)

    def _fetch_collateral(self):

        json = None

        try:

            json = self._json_get('/v1/me/getcollateralaccounts')

        except Exception as e:

            self.__log.debug('Collateral Failure : %s - %s', type(e), e.args)

        for ccy, unit in self.__collateral.items():

            value = None

            for asset in json if json is not None else []:

                if 'currency_code' not in asset:
                    continue

                if ccy != asset['currency_code']:
                    continue

                value = asset['amount'] if 'amount' in asset else None

            g = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, unit)
            g.update_value(self.__LABEL_MARGIN, ccy, value)
            self.__log.debug('Margin : %s = %s', ccy, value)

            if unit == UnitType.BTC:
                btc_ticker = self.__context.get_ticker_gauges(self.__site, ProductType.JPY_BTC)
                btc_price = btc_ticker.get_cached_mid('BTC_JPY')

                jpy = value * btc_price \
                    if value is not None and btc_price is not None \
                    else None

                account = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
                account.update_value(self.__LABEL_MARGIN, ccy, jpy)

    def _fetch_margin(self):

        for code, unit in self.__margins.items():

            json = None

            try:

                json = self._json_get('/v1/me/getpositions?product_code=' + code)

            except Exception as e:

                self.__log.debug('Margin Failure : %s - %s', type(e), e.args)

            quantity = 0.0
            unrealized = 0.0

            for position in json if json is not None else []:

                if 'side' not in position or position['side'] is None:
                    continue

                if 'size' not in position or position['size'] is None:
                    continue

                if 'pnl' not in position or position['pnl'] is None:
                    continue

                quantity += (position['size'] * (1 if position['side'] == 'BUY' else -1))
                unrealized += position['pnl']

            jpy = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, unit)
            jpy.update_value(self.__LABEL_MARGIN, code, quantity)

            jpy = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
            jpy.update_value(self.__LABEL_MARGIN, code, unrealized)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = BitflyerAccount(context)
    target.start()


if __name__ == '__main__':
    main()
