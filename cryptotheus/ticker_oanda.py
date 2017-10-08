from os import getenv
from threading import Thread
from time import sleep
from urllib import parse

from requests import request

from cryptotheus.context import ProductType, CryptotheusContext


class OandaTicker(Thread):
    @staticmethod
    def get_site():
        return 'oanda'

    @staticmethod
    def get_code(product):
        if product == ProductType.JPY_USD:
            return 'USD_JPY'
        if product == ProductType.JPY_EUR:
            return 'EUR_JPY'
        return None

    def __init__(self, context,
                 endpoint=getenv('oanda_endpoint', 'https://api-fxtrade.oanda.com/v1/prices?instruments='),
                 interval=getenv('oanda_interval', 15),
                 token=getenv('oanda_token', None)
                 ):
        super(OandaTicker, self).__init__()
        self.__site = OandaTicker.get_site()
        self.__targets = {
            OandaTicker.get_code(ProductType.JPY_USD): ProductType.JPY_USD,
            OandaTicker.get_code(ProductType.JPY_EUR): ProductType.JPY_EUR,
        }
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval
        self.__token = token

    def run(self):

        log = self.__context.get_logger(self)

        while self.__context.is_active():

            json = {}

            if self.__token is not None:

                try:

                    # Single request can contain multiple products.
                    products = parse.quote(','.join(self.__targets.keys()))

                    headers = {
                        "Authorization": "Bearer " + self.__token
                    }

                    # {'prices': [{p1}, {p2}, ...]
                    json = request('GET', self.__endpoint + products, headers=headers).json()

                except Exception as e:

                    log.debug('%s : %s', type(e), e.args)

            for code, product in self.__targets.items():

                ask = None
                bid = None

                for price in json['prices'] if 'prices' in json else []:

                    if 'status' in price and 'halted' == price['status']:
                        continue

                    if 'instrument' not in price:
                        continue

                    if code != price['instrument']:
                        continue

                    ask = price['ask'] if 'ask' in price else None
                    bid = price['bid'] if 'bid' in price else None
                    break

                gauges = self.__context.get_ticker_gauges(self.__site, product)
                gauges.update_bbo(code, ask, bid)
                log.debug('%s : ask=%s bid=%s', code, ask, bid)

            sleep(self.__interval)


def main():
    context = CryptotheusContext(debug=True)
    context.launch_server()

    target = OandaTicker(context)
    target.start()


if __name__ == '__main__':
    main()
