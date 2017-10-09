from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext
from cryptotheus.ticker_oanda import OandaTicker


class BitmexTicker(Thread):
    def __init__(self, context,
                 endpoint=getenv('bitmex_endpoint', 'https://www.bitmex.com/api/v1/quote?count=1&reverse=true&symbol='),
                 interval=getenv('bitmex_interval', 15)
                 ):
        super(BitmexTicker, self).__init__()
        self.__site = 'bitmex'
        self.__targets = {
            'XBTUSD': ProductType.USD_BTC,
        }
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval

    def run(self):

        while self.__context.is_active():

            threads = []

            for code, product in self.__targets.items():
                threads.append(Thread(daemon=True, target=self.fetch, args=[code, product]))

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            sleep(self.__interval)

    def fetch(self, code, product):

        log = self.__context.get_logger(self)
        ask = None
        bid = None

        try:

            records = get(self.__endpoint + code).json()

            for json in records if records is not None else []:

                if 'symbol' not in json:
                    continue

                if code != json['symbol']:
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
