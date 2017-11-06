from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.context import ProductType, CryptotheusContext


class QuoineTicker(Thread):
    def __init__(self, context,
                 endpoint=getenv('quoine_endpoint', 'https://api.quoine.com/products'),
                 interval=getenv('quoine_interval', 15)
                 ):
        super(QuoineTicker, self).__init__()
        self.__site = 'quoine'
        self.__targets = {
            'BTCJPY': ProductType.JPY_BTC,
            'BTCUSD': ProductType.USD_BTC,
            'ETHBTC': ProductType.BTC_ETH,
        }
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval

    def run(self):

        log = self.__context.get_logger(self)

        while self.__context.is_active():

            products = []

            try:

                products = get(self.__endpoint).json()

            except BaseException as e:

                log.warn('%s : %s', type(e), e.args)

            for code, product in self.__targets.items():

                ask = None
                bid = None
                ltp = None

                for json in products if products is not None else []:

                    if 'currency_pair_code' in json and code == json['currency_pair_code']:
                        ask = json['market_ask'] if 'market_ask' in json else None
                        bid = json['market_bid'] if 'market_bid' in json else None
                        ltp = json['last_traded_price'] if 'last_traded_price' in json else None
                        break

                gauges = self.__context.get_ticker_gauges(self.__site, product)
                gauges.update_bbo(code, ask, bid)
                gauges.update_ltp(code, ltp)
                log.debug('%s : ask=%s bid=%s ltp=%s', code, ask, bid, ltp)

            sleep(self.__interval)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = QuoineTicker(context)
    target.start()


if __name__ == '__main__':
    main()
