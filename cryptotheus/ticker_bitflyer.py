from logging import DEBUG
from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.ticker_context import ProductType, TickerContext


class BitflyerThread(Thread):
    __SITE = 'bitflyer'
    __TARGET_PATH = getenv(__SITE + '_addr', 'https://api.bitflyer.jp/v1/ticker?product_code=')
    __TARGET_TIME = getenv(__SITE + '_time', 15)

    __TARGETS = {
        'BTC_JPY': ProductType.JPY_BTC,
        'FX_BTC_JPY': ProductType.JPY_BTC,
        'BTCJPY_MAT1WK': ProductType.JPY_BTC,
        'BTCJPY_MAT2WK': ProductType.JPY_BTC,
        'BCH_BTC': ProductType.BTC_BCH,
        'ETH_BTC': ProductType.BTC_ETH,
    }

    __context = None

    def __init__(self, context):
        super(BitflyerThread, self).__init__()
        self.__context = context

    def run(self):

        while True:

            threads = []

            for code, product in self.__class__.__TARGETS.items():
                t = Thread(target=self.fetch, args=[code, product])
                t.setDaemon(True)
                t.start()
                threads.append(t)

            [t.join() for t in threads]

            sleep(self.__class__.__TARGET_TIME)

    def fetch(self, code, product):

        log = self.__context.get_logger(self.__class__.__SITE)
        ask = None
        bid = None
        mid = None
        ltp = None

        try:

            json = get(self.__class__.__TARGET_PATH + code).json()

            ltp = json['ltp'] if 'ltp' in json else None
            ask = json['best_ask'] if 'best_ask' in json else None
            bid = json['best_bid'] if 'best_bid' in json else None
            mid = (ask + bid) * 0.5 if (ask is not None and bid is not None) else None

            log.debug('Fetched : %s={ask=%s, bid=%s, ltp=%s}', code, ask, bid, ltp)

        except Exception as e:

            log.debug('Failure %s : %s', type(e), e.args)

        gauges = self.__context.get_ticker_gauges(self.__class__.__SITE, product)
        gauges.update_bbo(code, ask, bid)
        gauges.update_mid(code, mid)
        gauges.update_ltp(code, ltp)


if __name__ == '__main__':
    context = TickerContext(log_level=DEBUG)
    context.launch_server()

    target = BitflyerThread(context)
    target.start()
