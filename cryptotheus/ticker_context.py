from enum import Enum
from logging import Formatter, StreamHandler, INFO, getLogger
from os import getenv
from threading import Lock

from prometheus_client import Gauge, start_http_server


class ProductType(Enum):
    JPY_BTC = 1
    USD_BTC = 2
    BTC_BCH = 3
    BTC_ETH = 4
    JPY_USD = 5


class TickerGauges(object):
    __LABEL_ASK = 'ask'
    __LABEL_BID = 'bid'

    __LCK = Lock()
    __BBO = {}
    __MID = {}
    __LTP = {}

    __site = None
    __product = None

    def __init__(self, site, product):
        self.__site = site
        self.__product = product

    def update_bbo(self, code, ask, bid):

        with TickerGauges.__LCK:
            g = TickerGauges.__BBO[self.__product] if self.__product in TickerGauges.__BBO else None

            if g is None:
                n = self.__product.name.lower()
                d = self.__product.name
                g = Gauge('ticker_bbo_' + n, 'Best bid/offer price for ' + d, ['site', 'product', 'type'])
                TickerGauges.__BBO[self.__product] = g

        g.labels(self.__site, code, self.__LABEL_ASK).set(float(ask) if ask is not None else None)
        g.labels(self.__site, code, self.__LABEL_BID).set(float(bid) if bid is not None else None)

    def update_mid(self, code, mid):

        with TickerGauges.__LCK:
            g = TickerGauges.__MID[self.__product] if self.__product in TickerGauges.__MID else None

            if g is None:
                n = self.__product.name.lower()
                d = self.__product.name
                g = Gauge('ticker_mid_' + n, 'Mid price for ' + d, ['site', 'product'])
                TickerGauges.__MID[self.__product] = g

        g.labels(self.__site, code).set(float(mid) if mid is not None else None)

    def update_ltp(self, code, ltp):

        with TickerGauges.__LCK:
            g = TickerGauges.__LTP[self.__product] if self.__product in TickerGauges.__LTP else None

            if g is None:
                n = self.__product.name.lower()
                d = self.__product.name
                g = Gauge('ticker_ltp_' + n, 'Mid price for ' + d, ['site', 'product'])
                TickerGauges.__LTP[self.__product] = g

        g.labels(self.__site, code).set(float(ltp) if ltp is not None else None)


class TickerContext(object):
    # Logger
    __loggers = {}
    __level = None

    # Metrics Server
    __listen_host = getenv('listen_host', 'localhost')
    __listen_port = getenv('listen_port', 10001)

    # Metrics (site -> product -> Gauge)
    __sites = {}

    def __init__(self, log_level=INFO):
        self.__level = log_level

    def get_ticker_gauges(self, site, product):

        site_gauges = self.__sites[site] if site in self.__sites else None

        if site_gauges is None:
            site_gauges = {}
            self.__sites[site] = site_gauges

        site_gauge = site_gauges[product] if product in site_gauges else None

        if site_gauge is None:
            site_gauge = TickerGauges(site, product)
            site_gauges[product] = site_gauge

        return site_gauge

    def get_logger(self, name):

        logger = self.__loggers[name] if name in self.__loggers else None

        if logger is None:
            formatter = Formatter(fmt='[%(asctime)-15s][%(levelname)-5s]%(message)s')
            handler = StreamHandler()
            handler.setFormatter(formatter)
            handler.setLevel(self.__level)
            logger = getLogger(name)
            logger.setLevel(handler.level)
            logger.addHandler(handler)
            self.__loggers[name] = logger

        return logger

    def launch_server(self):

        start_http_server(self.__listen_port, addr=self.__listen_host)
