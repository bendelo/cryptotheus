from logging import DEBUG
from os import getenv
from threading import Thread
from time import sleep

from requests import get

from cryptotheus.ticker_context import ProductType, TickerContext


class PoloniexThread(Thread):
    __SITE = 'poloniex'
    __TARGET_PATH = getenv(__SITE + '_addr', 'https://poloniex.com/public?command=returnTicker')
    __TARGET_TIME = getenv(__SITE + '_time', 15)

    __TARGETS = {
        'USDT_BTC': ProductType.USD_BTC,
        'BTC_BCH': ProductType.BTC_BCH,
        'BTC_ETH': ProductType.BTC_ETH,
    }

    __context = None

    def __init__(self, context):
        super(PoloniexThread, self).__init__()
        self.__context = context

    def run(self):

        log = self.__context.get_logger(self.__class__.__SITE)

        while True:

            try:

                # Single request contains all products
                jsons = get(self.__class__.__TARGET_PATH).json()

                for code, product in self.__class__.__TARGETS.items():
                    json = jsons[code] if code in jsons else None

                    ltp = json['last'] if 'last' in json else None
                    ask = json['lowestAsk'] if 'lowestAsk' in json else None
                    bid = json['highestBid'] if 'highestBid' in json else None
                    mid = (float(ask) + float(bid)) * 0.5 if (ask is not None and bid is not None) else None

                    gauges = self.__context.get_ticker_gauges(self.__class__.__SITE, product)
                    gauges.update_bbo(code, ask, bid)
                    gauges.update_mid(code, mid)
                    gauges.update_ltp(code, ltp)

                    log.debug('Fetched : %s={ask=%s, bid=%s, ltp=%s}', code, ask, bid, ltp)

            except Exception as e:

                log.debug('Failure %s : %s', type(e), e.args)

                for code, product in self.__TARGETS.items():
                    gauges = self.__context.get_ticker_gauges(self.__class__.__SITE, product)
                    gauges.update_bbo(code, None, None)
                    gauges.update_mid(code, None)
                    gauges.update_ltp(code, None)

            sleep(self.__class__.__TARGET_TIME)


if __name__ == '__main__':
    context = TickerContext(log_level=DEBUG)
    context.launch_server()

    target = PoloniexThread(context)
    target.start()
