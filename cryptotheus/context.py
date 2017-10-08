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
    JPY_EUR = 6


class AccountType(Enum):
    BALANCE = 1


class UnitType(Enum):
    JPY = 1
    USD = 2
    BTC = 3
    ETH = 4
    BCH = 5


class TickerGauges(object):
    __LABEL_ASK = 'ask'
    __LABEL_BID = 'bid'
    __VALUE_NIL = 0.0

    __LCK = Lock()
    __BBO = {}
    __MID = {}
    __LTP = {}

    __cached_ask = {}
    __cached_bid = {}
    __cached_mid = {}
    __cached_ltp = {}

    def __init__(self, site, product):
        self.__site = site
        self.__product = product

    def __get_gauge(self, gauges, prefix, description):
        with TickerGauges.__LCK:
            gauge = gauges[self.__product] if self.__product in gauges else None

            if gauge is None:
                n = self.__product.name.lower()
                d = self.__product.name
                gauge = Gauge(prefix + n, description + d, ['id'])
                gauges[self.__product] = gauge

        return gauge

    def update_bbo(self, code, ask, bid, mid=None, nil=__VALUE_NIL):
        a = float(ask) if ask is not None else None
        b = float(bid) if bid is not None else None
        g = self.__get_gauge(TickerGauges.__BBO, 'ticker_bbo_', 'Best bid/offer price for ')
        g.labels("%s:%s:%s" % (self.__site, code, self.__LABEL_ASK)).set(a if a is not None else nil)
        g.labels("%s:%s:%s" % (self.__site, code, self.__LABEL_BID)).set(b if b is not None else nil)

        m = (float(ask) + float(bid)) * 0.5 if mid is None and ask is not None and bid is not None else mid
        g = self.__get_gauge(TickerGauges.__MID, 'ticker_mid_', 'Mid price for ')
        g.labels("%s:%s" % (self.__site, code)).set(m if m is not None else nil)

        self.__cached_ask[code] = a
        self.__cached_bid[code] = b
        self.__cached_mid[code] = m

    def update_ltp(self, code, ltp, nil=__VALUE_NIL):
        p = float(ltp) if ltp is not None else None
        g = self.__get_gauge(TickerGauges.__LTP, 'ticker_ltp_', 'Last trade price for ')
        g.labels("%s:%s" % (self.__site, code)).set(p if p is not None else nil)

        self.__cached_ltp[code] = p

    def get_cached_ask(self, code):
        return self.__cached_ask[code] if code in self.__cached_ask else None

    def get_cached_bid(self, code):
        return self.__cached_bid[code] if code in self.__cached_bid else None

    def get_cached_mid(self, code):
        return self.__cached_mid[code] if code in self.__cached_mid else None

    def get_cached_ltp(self, code):
        return self.__cached_ltp[code] if code in self.__cached_ltp else None


class AccountGauges(object):
    __NIL = 0.0
    __LCK = Lock()
    __MAP = {}

    def __init__(self, site, account, unit):
        self.__site = site
        self.__account = account
        self.__unit = unit

    def __get_gauge(self):

        with AccountGauges.__LCK:

            units = AccountGauges.__MAP[self.__account] if self.__account in AccountGauges.__MAP else None

            if units is None:
                units = {}
                AccountGauges.__MAP[self.__account] = units

            gauge = units[self.__unit] if self.__unit in units else None

            if gauge is None:
                s = 'account_%s_%s' % (self.__account.name.lower(), self.__unit.name.lower())
                d = 'Account %s in %s' % (self.__account.name.lower(), self.__unit.name)
                gauge = Gauge(s, d, ['site', 'type', 'name'])
                units[self.__unit] = gauge

        return gauge

    def update_value(self, account_type, name, value):
        v = value if value is not None else self.__NIL
        gauge = self.__get_gauge()
        gauge.labels(self.__site, account_type, name).set(v)


class CryptotheusContext(object):
    # Metrics Server
    __HOST = getenv('metric_host', 'localhost')
    __PORT = getenv('metric_port', 10001)

    # Logger
    __loggers = {}

    # Ticker Metrics
    __tickers = {}

    # Account Metrics
    __accounts = {}

    # State
    __active = True

    def __init__(self, log_level=INFO, host=__HOST, port=__PORT):
        self.__level = log_level
        self.__host = host
        self.__port = port

    def get_logger(self, source):

        name = source.__class__.__name__

        logger = self.__loggers[name] if name in self.__loggers else None

        if logger is None:
            formatter = Formatter(fmt='[%(asctime)-15s][%(levelname)-5s][%(name)s] %(message)s')
            handler = StreamHandler()
            handler.setFormatter(formatter)
            handler.setLevel(self.__level)
            logger = getLogger(name)
            logger.setLevel(handler.level)
            logger.addHandler(handler)
            self.__loggers[name] = logger

        return logger

    def launch_server(self):

        self.get_logger(self).info('Starting server [%s:%s]', self.__host, self.__port)

        start_http_server(self.__port, addr=self.__host)

    def is_active(self):
        return self.__active

    def get_ticker_gauges(self, site, product):

        products = self.__tickers[site] if site in self.__tickers else None

        if products is None:
            products = {}
            self.__tickers[site] = products

        gauges = products[product] if product in products else None

        if gauges is None:
            gauges = TickerGauges(site, product)
            products[product] = gauges

        return gauges

    def get_account_gauges(self, site, account, unit):

        accounts = self.__accounts[site] if site in self.__accounts else None

        if accounts is None:
            accounts = {}
            self.__accounts[site] = accounts

        units = accounts[account] if account in accounts else None

        if units is None:
            units = {}
            accounts[account] = units

        gauges = units[unit] if unit in units else None

        if gauges is None:
            gauges = AccountGauges(site, account, unit)
            units[unit] = gauges

        return gauges
