from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext


class CoincheckTicker(Thread):
    def __init__(self, context,
                 endpoint=getenv('coincheck_endpoint', 'https://coincheck.com/api/ticker'),
                 interval=getenv('coincheck_interval', 15)
                 ):
        super(CoincheckTicker, self).__init__()
        self.__site = 'coincheck'
        self.__targets = {
            'btc_jpy': ProductType.JPY_BTC,
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

            # No code appended. (Only one product available)
            json = get(self.__endpoint).json()

            ltp = json['last'] if 'last' in json else None
            ask = json['ask'] if 'ask' in json else None
            bid = json['bid'] if 'bid' in json else None

            log.debug('%s : ask=%s bid=%s ltp=%s', code, ask, bid, ltp)

        except Exception as e:

            log.warn('%s : %s', type(e), e.args)

        gauges = self.__context.get_ticker_gauges(self.__site, product)
        gauges.update_bbo(code, ask, bid)
        gauges.update_ltp(code, ltp)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = CoincheckTicker(context)
    target.start()


if __name__ == '__main__':
    main()
