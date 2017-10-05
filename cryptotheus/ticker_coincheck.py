from logging import DEBUG
from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.ticker_context import ProductType, TickerContext


class CoincheckThread(Thread):
    __SITE = 'coincheck'
    __TARGET_PATH = getenv(__SITE + '_addr', 'https://coincheck.com/api/ticker')
    __TARGET_TIME = getenv(__SITE + '_time', 15)

    __TARGETS = {
        'btc_jpy': ProductType.JPY_BTC,
    }

    __context = None

    def __init__(self, context):
        super(CoincheckThread, self).__init__()
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

            # No code appended. (Only one product available)
            json = get(self.__class__.__TARGET_PATH).json()

            ltp = json['last'] if 'last' in json else None
            ask = json['ask'] if 'ask' in json else None
            bid = json['bid'] if 'bid' in json else None
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

    target = CoincheckThread(context)
    target.start()
