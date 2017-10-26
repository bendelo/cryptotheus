from datetime import timedelta, datetime
from hashlib import sha256
from hmac import new
from os import getenv
from threading import Thread
from time import sleep, time

from requests import request

from cryptotheus.context import AccountType, UnitType, ProductType, CryptotheusContext


class BitflyerAccount(Thread):
    __LABEL_CASH = 'cash'
    __LABEL_MARGIN = 'margin'
    __LABEL_COLLATERAL = 'collateral'

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
        self.__products = {
            'BTC_JPY': UnitType.JPY,
            'ETH_BTC': UnitType.BTC,
            'BCH_BTC': UnitType.BTC,
            'FX_BTC_JPY': UnitType.JPY,
            'BTCJPY_MAT1WK': UnitType.JPY,
            'BTCJPY_MAT2WK': UnitType.JPY,
        }
        self.__intervals = {
            '01H': timedelta(hours=1),
            '06H': timedelta(hours=6),
            '12H': timedelta(hours=12),
            '01D': timedelta(days=1),
            '07D': timedelta(days=7),
            '30D': timedelta(days=30),
        }
        self.__log = context.get_logger(self)
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval
        self.__key = key
        self.__secret = secret

    def run(self):

        while self.__context.is_active():

            # Sleep first, to cache the prices
            sleep(self.__interval)

            threads = [
                Thread(daemon=True, target=self._fetch_balance),
                Thread(daemon=True, target=self._fetch_collateral),
                Thread(daemon=True, target=self._fetch_collateral_account),
                Thread(daemon=True, target=self._fetch_margin),
                Thread(daemon=True, target=self._fetch_execution),
            ]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

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

    def _to_jpy(self, unit, value):

        if unit == UnitType.JPY:
            return value

        btc = value if unit == UnitType.BTC else self._to_btc(unit, value)

        rate = self.__context.get_ticker_gauges(self.__site, ProductType.JPY_BTC).get_cached_mid('BTC_JPY')

        return btc * rate if btc is not None and rate is not None else None

    def _to_btc(self, unit, value):

        if unit == UnitType.BTC:
            return value

        rate = None

        if unit == UnitType.ETH:
            rate = self.__context.get_ticker_gauges(self.__site, ProductType.BTC_ETH).get_cached_mid('ETH_BTC')

        if unit == UnitType.BCH:
            rate = self.__context.get_ticker_gauges(self.__site, ProductType.BTC_BCH).get_cached_mid('BCH_BTC')

        return value * rate if value is not None and rate is not None else None

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

            if unit != UnitType.JPY:
                jpy = self._to_jpy(unit, value)
                g = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
                g.update_value(self.__LABEL_CASH, ccy, jpy)

            if unit != UnitType.JPY and unit != UnitType.BTC:
                btc = self._to_btc(unit, value)
                g = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.BTC)
                g.update_value(self.__LABEL_CASH, ccy, btc)

    def _fetch_collateral(self):

        json = {}

        try:

            json = self._json_get('/v1/me/getcollateral')

        except Exception as e:

            self.__log.debug('Collateral Failure : %s - %s', type(e), e.args)

        g = self.__context.get_account_gauges(self.__site, AccountType.COLLATERAL, UnitType.JPY)

        value = json['collateral'] if 'collateral' in json else None
        g.update_value('deposited', UnitType.JPY.name, value)

        pl = json['open_position_pnl'] if 'open_position_pnl' in json else None
        g.update_value('unrealized', UnitType.JPY.name, pl)

        required = json['require_collateral'] if 'require_collateral' in json else None
        g.update_value('required', UnitType.JPY.name, required)

        self.__log.debug('Collateral : deposited = %s, unrealized = %s, required = %s', value, pl, required)

    def _fetch_collateral_account(self):

        json = None

        try:

            json = self._json_get('/v1/me/getcollateralaccounts')

        except Exception as e:

            self.__log.debug('Collateral Account Failure : %s - %s', type(e), e.args)

        for ccy, unit in self.__collateral.items():

            value = None

            for asset in json if json is not None else []:

                if 'currency_code' not in asset:
                    continue

                if ccy != asset['currency_code']:
                    continue

                value = asset['amount'] if 'amount' in asset else None

            g = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, unit)
            g.update_value(self.__LABEL_COLLATERAL, ccy, value)
            self.__log.debug('Collateral Account : %s = %s', ccy, value)

            if unit != UnitType.JPY:
                account = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
                account.update_value(self.__LABEL_COLLATERAL, ccy, self._to_jpy(unit, value))

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

            self.__log.debug('Margin : %s - quantity=%s unrealized=%s', code, quantity, unrealized)

            ccy = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, unit)
            ccy.update_value(self.__LABEL_MARGIN, code, quantity)

            jpy = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.JPY)
            jpy.update_value(self.__LABEL_MARGIN, code, unrealized)

    def _fetch_execution(self):

        now = datetime.now()

        for code, unit in self.__products.items():

            interval_notional = {}

            try:

                minimum_id = None

                notionals = {}

                for interval in self.__intervals.keys():
                    notionals[interval] = 0.0

                while True:

                    path = '/v1/me/getexecutions?count=500&product_code=%s' % code

                    if minimum_id is not None:
                        path = path + '&before=%s' % minimum_id

                    json = self._json_get(path)

                    count = 0

                    for execution in json if json is not None else []:

                        if 'id' not in execution:
                            continue

                        if 'price' not in execution:
                            continue

                        if 'size' not in execution:
                            continue

                        if 'exec_date' not in execution:
                            continue

                        if minimum_id is None:
                            minimum_id = execution['id']
                        else:
                            minimum_id = min(minimum_id, execution['id'])

                        exec_date = execution['exec_date'][:19] + ' +0000'

                        exec_date = datetime.strptime(exec_date, '%Y-%m-%dT%H:%M:%S %z')

                        for interval, delta in self.__intervals.items():

                            if (exec_date + delta).timestamp() < now.timestamp():
                                continue

                            notional = float(execution['price']) * float(execution['size'])

                            notionals[interval] = notionals[interval] + notional

                            count = count + 1

                    if count == 0:
                        break

                self.__log.debug('Volume : %s - %s' % (code, str(notionals)))

                interval_notional = notionals

            except Exception as e:

                self.__log.debug('Volume Failure : %s - %s', type(e), e.args)

            for interval in self.__intervals.keys():
                notional = interval_notional[interval] if interval in interval_notional else None
                ccy = self.__context.get_account_gauges(self.__site, AccountType.VOLUME, unit)
                ccy.update_value(interval, code, notional)
                jpy = self.__context.get_account_gauges(self.__site, AccountType.VOLUME, UnitType.JPY)
                jpy.update_value(interval, code, self._to_jpy(unit, notional))


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = BitflyerAccount(context)
    target.start()


if __name__ == '__main__':
    main()
