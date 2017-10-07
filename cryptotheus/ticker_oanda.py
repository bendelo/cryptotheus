from logging import DEBUG
from os import getenv
from threading import Thread
from time import sleep
from urllib import parse

from requests import request

from cryptotheus.context import ProductType, CryptotheusContext


class OandaThread(Thread):
    __SITE = 'oanda'
    __ENDPOINT = getenv(__SITE + '_endpoint', 'https://api-fxtrade.oanda.com/v1/prices?instruments=')
    __INTERVAL = getenv(__SITE + '_interval', 15)
    __TOKEN = getenv(__SITE + '_token', '')
    __TARGETS = {
        'USD_JPY': ProductType.JPY_USD,
        'EUR_JPY': ProductType.JPY_EUR,
    }

    def __init__(self, context, endpoint=__ENDPOINT, interval=__INTERVAL, token=__TOKEN):
        super(OandaThread, self).__init__()
        self.__site = self.__SITE
        self.__targets = self.__TARGETS
        self.__context = context
        self.__endpoint = endpoint
        self.__interval = interval
        self.__token = token

    def run(self):

        log = self.__context.get_logger(self.__site)

        while self.__context.is_active():

            json = []

            try:

                # Single request can contain multiple products.
                products = parse.quote(','.join(self.__targets.keys()))

                headers = {
                    "Authorization": "Bearer " + self.__token
                }

                # {'prices': [{p1}, {p2}, ...]
                json = request('GET', self.__endpoint + products, headers=headers).json()

            except Exception as e:

                log.debug('Failure : %s - %s', type(e), e.args)

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
                log.debug('Fetched : %s={ask=%s, bid=%s}', code, ask, bid)

            sleep(self.__interval)


def main():
    context = CryptotheusContext(log_level=DEBUG)
    context.launch_server()

    target = OandaThread(context)
    target.start()


if __name__ == '__main__':
    main()
