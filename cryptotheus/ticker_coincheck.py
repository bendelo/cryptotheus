from logging import DEBUG
from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext


class CoincheckThread(Thread):
    __SITE = 'coincheck'
    __ENDPOINT = getenv(__SITE + '_endpoint', 'https://coincheck.com/api/ticker')
    __INTERVAL = getenv(__SITE + '_interval', 15)
    __TARGETS = {
        'btc_jpy': ProductType.JPY_BTC,
    }

    def __init__(self, context, endpoint=__ENDPOINT, interval=__INTERVAL):
        super(CoincheckThread, self).__init__()
        self.__site = self.__SITE
        self.__targets = self.__TARGETS
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

            # No code appended. (Only one product available)
            json = get(self.__endpoint).json()

            ltp = json['last'] if 'last' in json else None
            ask = json['ask'] if 'ask' in json else None
            bid = json['bid'] if 'bid' in json else None

            log.debug('Fetched : %s={ask=%s, bid=%s, ltp=%s}', code, ask, bid, ltp)

        except Exception as e:

            log.debug('Failure : %s - %s', type(e), e.args)

        gauges = self.__context.get_ticker_gauges(self.__site, product)
        gauges.update_bbo(code, ask, bid)
        gauges.update_ltp(code, ltp)


def main():
    context = CryptotheusContext(log_level=DEBUG)
    context.launch_server()

    target = CoincheckThread(context)
    target.start()


if __name__ == '__main__':
    main()
