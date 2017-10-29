from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext
from cryptotheus.ticker_oanda import OandaTicker


class BitmexTicker(Thread):
    def __init__(self, context,
                 endpoint=getenv('bitmex_endpoint', 'https://www.bitmex.com'),
                 interval=getenv('bitmex_interval', 15)
                 ):
        super(BitmexTicker, self).__init__()
        self.__site = 'bitmex'
        self.__targets = {
            'XBTUSD': ProductType.USD_BTC,
            'XBT_QT': ProductType.USD_BTC,
            'XBJ_QT': ProductType.JPY_BTC,
            'ETH_QT': ProductType.BTC_ETH,
        }
        self.__symbols = {
            'XBTUSD': 'XBT:perpetual',
            'XBT_QT': 'XBT:quarterly',
            'XBJ_QT': 'XBJ:quarterly',
            'ETH_QT': 'ETH:quarterly',
        }
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval

    def run(self):

        while self.__context.is_active():

            mappings = self.mappings()

            threads = []

            for code, product in self.__targets.items():
                threads.append(Thread(daemon=True, target=self.fetch, args=[mappings, code, product]))

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            sleep(self.__interval)

    def mappings(self):

        log = self.__context.get_logger(self)

        mappings = {}

        try:

            json = get(self.__endpoint + '/api/v1/instrument/activeIntervals').json()

            intervals = json['intervals']
            symbols = json['symbols']

            for index, interval in enumerate(intervals):
                mappings[interval] = symbols[index]

        except Exception as e:

            log.debug('%s : %s', type(e), e.args)

        return mappings

    def fetch(self, mappings, code, product):

        log = self.__context.get_logger(self)
        ask = None
        bid = None

        try:

            symbol = mappings[self.__symbols[code]]

            records = get(self.__endpoint + '/api/v1/quote?count=1&reverse=true&symbol=' + symbol).json()

            for json in records if records is not None else []:

                if 'symbol' not in json:
                    continue

                if symbol != json['symbol']:
                    continue

                ask = json['askPrice'] if 'askPrice' in json else None
                bid = json['bidPrice'] if 'bidPrice' in json else None
                break

            log.debug('%s : ask=%s bid=%s', code, ask, bid)

        except Exception as e:

            log.debug('%s : %s', type(e), e.args)

        gauges = self.__context.get_ticker_gauges(self.__site, product)
        gauges.update_bbo(code, ask, bid)

        if product == ProductType.USD_BTC:
            ticker = self.__context.get_ticker_gauges(OandaTicker.get_site(), ProductType.JPY_USD)
            rate = ticker.get_cached_mid(OandaTicker.get_code(ProductType.JPY_USD))
            j_ask = float(ask) * float(rate) if ask is not None and rate is not None else None
            j_bid = float(bid) * float(rate) if bid is not None and rate is not None else None
            self.__context.get_ticker_gauges(self.__site, ProductType.JPY_BTC).update_bbo(code, j_ask, j_bid)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = BitmexTicker(context)
    target.start()


if __name__ == '__main__':
    main()
