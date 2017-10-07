from logging import DEBUG
from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext


class BitmexThread(Thread):
    __SITE = 'bitmex'
    __ENDPOINT = getenv(__SITE + '_endpoint', 'https://www.bitmex.com/api/v1/quote?count=1&reverse=true&symbol=')
    __INTERVAL = getenv(__SITE + '_interval', 15)
    __TARGETS = {
        'XBTUSD': ProductType.USD_BTC,
    }

    def __init__(self, context, endpoint=__ENDPOINT, interval=__INTERVAL):
        super(BitmexThread, self).__init__()
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

            log.debug('Fetched : %s={ask=%s, bid=%s}', code, ask, bid)

        except Exception as e:

            log.debug('Failure : %s - %s', type(e), e.args)

        gauges = self.__context.get_ticker_gauges(self.__site, product)
        gauges.update_bbo(code, ask, bid)


def main():
    context = CryptotheusContext(log_level=DEBUG)
    context.launch_server()

    target = BitmexThread(context)
    target.start()


if __name__ == '__main__':
    main()
