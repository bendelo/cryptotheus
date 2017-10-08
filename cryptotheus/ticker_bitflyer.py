from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext


class BitflyerTicker(Thread):
    def __init__(self, context,
                 endpoint=getenv('bitflyer_endpoint', 'https://api.bitflyer.jp'),
                 interval=getenv('bitflyer_interval', 15)
                 ):
        super(BitflyerTicker, self).__init__()
        self.__site = 'bitflyer'
        self.__targets = {
            'BTC_JPY': ProductType.JPY_BTC,
            'FX_BTC_JPY': ProductType.JPY_BTC,
            'BTCJPY_MAT1WK': ProductType.JPY_BTC,
            'BTCJPY_MAT2WK': ProductType.JPY_BTC,
            'BCH_BTC': ProductType.BTC_BCH,
            'ETH_BTC': ProductType.BTC_ETH,
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
        ltp = None

        try:

            json = get(self.__endpoint + '/v1/ticker?product_code=' + code).json()

            ltp = json['ltp'] if 'ltp' in json else None
            ask = json['best_ask'] if 'best_ask' in json else None
            bid = json['best_bid'] if 'best_bid' in json else None

            log.debug('%s : ask=%s bid=%s ltp=%s', code, ask, bid, ltp)

        except Exception as e:

            log.debug('%s : %s', type(e), e.args)

        gauges = self.__context.get_ticker_gauges(self.__site, product)
        gauges.update_bbo(code, ask, bid)
        gauges.update_ltp(code, ltp)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = BitflyerTicker(context)
    target.start()


if __name__ == '__main__':
    main()
