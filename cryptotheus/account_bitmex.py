from datetime import timedelta, datetime
from hashlib import sha256
from hmac import new
from os import getenv
from threading import Lock
from threading import Thread
from time import sleep, time
from urllib import parse

from requests import request

from cryptotheus.context import AccountType, UnitType, CryptotheusContext


class BitmexAccount(Thread):
    __SATOSHI = 0.00000001

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
        self.__positions = {
            'XBT:perpetual': UnitType.BTC,
            'XBT:quarterly': UnitType.BTC,
            'XBJ:quarterly': UnitType.BTC
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
        self.__lock = Lock()

    def run(self):

        while self.__context.is_active():

            mappings = self._get_mapping()

            threads = [
                Thread(daemon=True, target=self._fetch_collateral),
                Thread(daemon=True, target=self._fetch_position, args=(mappings,)),
                Thread(daemon=True, target=self._fetch_execution, args=(mappings,)),
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

        with self.__lock:

            sleep(0.001)

            timestamp = str(int(time() * 1000))

            data = method + path + timestamp + body

            digest = new(str.encode(self.__secret), str.encode(data), sha256).hexdigest()

            headers = {
                "api-key": self.__key,
                "api-nonce": timestamp,
                "api-signature": digest,
                "Accept": "application/json"
            }

            result = request('GET', self.__endpoint + path, headers=headers).json()

        return result

    def _get_mapping(self):

        try:

            json = self._json_get('/api/v1/instrument/activeIntervals')

            intervals = json['intervals'] if 'intervals' in json else []

            symbols = json['symbols'] if 'symbols' in json else []

            mappings = {}

            for index, interval in enumerate(intervals):
                mappings[interval] = symbols[index]

            return mappings

        except Exception as e:

            self.__log.debug('Mapping Failure : %s - %s', type(e), e.args)

            return {}

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

                val = (asset['walletBalance'] * self.__SATOSHI) if 'walletBalance' in asset else None
                upl = (asset['unrealisedPnl'] * self.__SATOSHI) if 'unrealisedPnl' in asset else None
                exc = (asset['excessMargin'] * self.__SATOSHI) if 'excessMargin' in asset else None

            g = self.__context.get_account_gauges(self.__site, AccountType.COLLATERAL, unit)
            g.update_value('deposited', ccy, val)
            g.update_value('unrealized', ccy, upl)
            g.update_value('excess', ccy, exc)
            self.__log.debug('Collateral : deposited = %s, unrealized = %s, excess = %s', val, upl, exc)

    def _fetch_position(self, mappings):

        try:

            json = self._json_get('/api/v1/position')

            initial = 0

        except Exception as e:

            json = []

            initial = None

            self.__log.debug('Position Failure : %s - %s', type(e), e.args)

        for alias, unit in self.__positions.items():

            symbol = mappings[alias] if alias in mappings else None

            current = initial if symbol is not None else None
            realized = initial if symbol is not None else None
            unrealized = initial if symbol is not None else None

            for position in json:

                if 'symbol' not in position or symbol != position['symbol']:
                    continue

                if 'currentQty' in position:
                    current = position['currentQty']

                if 'realisedPnl' in position:
                    realized = position['realisedPnl']
                    realized = realized * self.__SATOSHI if realized is not None else None

                if 'unrealisedPnl' in position:
                    unrealized = position['unrealisedPnl']
                    unrealized = unrealized * self.__SATOSHI if unrealized is not None else None

                break

            g = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, unit)
            g.update_value('position', alias, current)

            g = self.__context.get_account_gauges(self.__site, AccountType.BALANCE, UnitType.BTC)
            g.update_value('realized', alias, realized)
            g.update_value('unrealized', alias, unrealized)

            self.__log.debug('Position %s (%s) : position = %s, realized = %s, unrealized = %s',
                             alias, symbol, current, realized, unrealized)

    def _fetch_execution(self, mappings):

        now = datetime.now()

        for alias, unit in self.__positions.items():

            symbol = mappings[alias] if alias in mappings else None

            end_time = None

            quantities = {}

            for interval in self.__intervals.keys():
                quantities[interval] = 0.0

            try:

                while True:

                    path = '/api/v1/execution/tradeHistory?count=500&reverse=true&symbol=' + parse.quote(symbol)

                    path = path if end_time is None else path + '&endTime=' + parse.quote(end_time)

                    json = self._json_get(path)

                    count = 0

                    for execution in json if json is not None else []:

                        if 'transactTime' not in execution or 'lastQty' not in execution:
                            continue

                        quantity = execution['lastQty']

                        end_time = execution['transactTime']

                        exec_date = datetime.strptime(end_time[:19] + ' +0000', '%Y-%m-%dT%H:%M:%S %z')

                        for interval, delta in self.__intervals.items():

                            if (exec_date + delta).timestamp() < now.timestamp():
                                continue

                            quantities[interval] = quantities[interval] + quantity

                            count = count + 1

                    if count == 0:
                        break

                self.__log.debug('Execution : %s - %s' % (alias, str(quantities)))

            except Exception as e:

                self.__log.debug('Execution Failure : %s - %s', type(e), e.args)

            for interval in self.__intervals.keys():
                g = self.__context.get_account_gauges(self.__site, AccountType.VOLUME, unit)
                g.update_value(interval, alias, quantities[interval])


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = BitmexAccount(context)
    target.start()


if __name__ == '__main__':
    main()
