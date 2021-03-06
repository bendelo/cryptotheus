from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext


class PoloniexTicker(Thread):
    def __init__(self, context,
                 endpoint=getenv('poloniex_endpoint', 'https://poloniex.com/public?command=returnTicker'),
                 interval=getenv('poloniex_interval', 15)
                 ):
        super(PoloniexTicker, self).__init__()
        self.__site = 'poloniex'
        self.__targets = {
            'USDT_BTC': ProductType.USD_BTC,
            'BTC_BCH': ProductType.BTC_BCH,
            'BTC_ETH': ProductType.BTC_ETH,
        }
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval

    def run(self):

        log = self.__context.get_logger(self)

        while self.__context.is_active():

            tickers = {}

            try:

                # Single request contains all products
                tickers = get(self.__endpoint).json()

            except Exception as e:

                log.warn('%s : %s', type(e), e.args)

            for code, product in self.__targets.items():
                json = tickers[code] if code in tickers else {}

                ltp = json['last'] if 'last' in json else None
                ask = json['lowestAsk'] if 'lowestAsk' in json else None
                bid = json['highestBid'] if 'highestBid' in json else None

                gauges = self.__context.get_ticker_gauges(self.__site, product)
                gauges.update_bbo(code, ask, bid)
                gauges.update_ltp(code, ltp)

                log.debug('%s : ask=%s bid=%s ltp=%s', code, ask, bid, ltp)

            sleep(self.__interval)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = PoloniexTicker(context)
    target.start()


if __name__ == '__main__':
    main()
