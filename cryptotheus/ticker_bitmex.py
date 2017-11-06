from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext


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

            instruments = self.instruments()

            self.extract(mappings, instruments)

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

            log.warn('%s : %s', type(e), e.args)

        return mappings

    def instruments(self):

        log = self.__context.get_logger(self)

        instruments = {}

        try:

            json = get(self.__endpoint + '/api/v1/instrument/activeAndIndices').json()

            for element in json:
                instruments[element['symbol']] = element

        except Exception as e:

            log.warn('%s : %s', type(e), e.args)

        return instruments

    def extract(self, mappings, instruments):

        log = self.__context.get_logger(self)

        for code, product in self.__targets.items():
            symbol = self.__symbols[code]
            symbol = mappings[symbol] if symbol in mappings else None

            instrument = instruments[symbol] if symbol in instruments else {}
            ask = instrument['askPrice'] if 'askPrice' in instrument else None
            bid = instrument['bidPrice'] if 'bidPrice' in instrument else None
            mid = instrument['midPrice'] if 'midPrice' in instrument else None
            ltp = instrument['lastPrice'] if 'lastPrice' in instrument else None

            gauges = self.__context.get_ticker_gauges(self.__site, product)
            gauges.update_bbo(code, ask, bid, mid=mid)
            gauges.update_ltp(code, ltp)
            log.debug('%s : ask=%s bid=%s mid=%s ltp=%s', code, ask, bid, mid, ltp)

            while 'referenceSymbol' in instrument:

                ref = instrument['referenceSymbol']

                if 'symbol' not in instrument or ref == instrument['symbol']:
                    break

                if ref not in instruments:
                    break

                instrument = instruments[ref]
                ltp = instrument['markPrice'] if 'markPrice' in instrument else None

                gauges.update_ltp(ref, ltp)
                log.debug('%s : mrk=%s', ref, ltp)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = BitmexTicker(context)
    target.start()


if __name__ == '__main__':
    main()
