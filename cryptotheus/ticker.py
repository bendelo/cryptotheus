import logging
import os
import threading

import requests
import time
from prometheus_client import Gauge, start_http_server

_BBO_JPY_BTC = Gauge('ticker_bbo_jpy_btc', 'Best bid/offer price for BTC denoted in JPY', ['site', 'product', 'type'])
_BBO_USD_BTC = Gauge('ticker_bbo_usd_btc', 'Best bid/offer price for BTC denoted in USD', ['site', 'product', 'type'])
_BBO_BTC_BCH = Gauge('ticker_bbo_btc_bch', 'Best bid/offer price for BCH denoted in BTC', ['site', 'product', 'type'])
_BBO_BTC_ETH = Gauge('ticker_bbo_btc_eth', 'Best bid/offer price for ETH denoted in BTC', ['site', 'product', 'type'])
_BBO_JPY_USD = Gauge('ticker_bbo_jpy_usd', 'Best bid/offer price for USD denoted in JPY', ['site', 'product', 'type'])

_MID_JPY_BTC = Gauge('ticker_mid_jpy_btc', 'Mid price for BTC denoted in JPY', ['site', 'product'])
_MID_USD_BTC = Gauge('ticker_mid_usd_btc', 'Mid price for BTC denoted in USD', ['site', 'product'])
_MID_BTC_BCH = Gauge('ticker_mid_btc_bch', 'Mid price for BCH denoted in BTC', ['site', 'product'])
_MID_BTC_ETH = Gauge('ticker_mid_btc_eth', 'Mid price for ETH denoted in BTC', ['site', 'product'])
_MID_JPY_USD = Gauge('ticker_mid_jpy_usd', 'Mid price for USD denoted in JPY', ['site', 'product'])

_LTP_JPY_BTC = Gauge('ticker_ltp_jpy_btc', 'Last trade price for BTC denoted in JPY', ['site', 'product'])
_LTP_USD_BTC = Gauge('ticker_ltp_usd_btc', 'Last trade price for BTC denoted in USD', ['site', 'product'])
_LTP_BTC_BCH = Gauge('ticker_ltp_btc_bch', 'Last trade price for BCH denoted in BTC', ['site', 'product'])
_LTP_BTC_ETH = Gauge('ticker_ltp_btc_eth', 'Last trade price for ETH denoted in BTC', ['site', 'product'])

_LABEL_ASK = 'ask'
_LABEL_BID = 'bid'

_format = logging.Formatter(fmt='[%(asctime)-15s][%(levelname)-5s]%(message)s')
_handler = logging.StreamHandler()
_handler.setFormatter(_format)
_handler.setLevel(logging.DEBUG)
_logger = logging.getLogger(__name__)
_logger.setLevel(_handler.level)
_logger.addHandler(_handler)


class BitflyerThread(threading.Thread):
    __site = 'bitflyer'
    __target_addr = os.getenv('bitflyer_addr', 'https://api.bitflyer.jp/v1/ticker?product_code=')
    __target_time = os.getenv('bitflyer_time', 15)

    def run(self):

        while True:

            try:

                self.fetch('BTC_JPY', _BBO_JPY_BTC, _MID_JPY_BTC, _LTP_JPY_BTC)

                self.fetch('FX_BTC_JPY', _BBO_JPY_BTC, _MID_JPY_BTC, _LTP_JPY_BTC)

                self.fetch('BTCJPY_MAT1WK', _BBO_JPY_BTC, _MID_JPY_BTC, _LTP_JPY_BTC)

                self.fetch('BTCJPY_MAT2WK', _BBO_JPY_BTC, _MID_JPY_BTC, _LTP_JPY_BTC)

                self.fetch('BCH_BTC', _BBO_BTC_BCH, _MID_BTC_BCH, _LTP_BTC_BCH)

                self.fetch('ETH_BTC', _BBO_BTC_ETH, _MID_BTC_ETH, _LTP_BTC_ETH)

            except Exception as e:

                _logger.debug('%s : %s', type(e), e.args)

            time.sleep(self.__target_time)

    def fetch(self, product, gauge_bbo, gauge_mid, gauge_ltp):

        tick = requests.get(self.__target_addr + product).json()
        _logger.debug('[%s][%s] %s', self.__site, product, tick)

        ask = tick['best_ask'] if 'best_ask' in tick else None
        bid = tick['best_bid'] if 'best_bid' in tick else None
        gauge_bbo.labels(self.__site, product, _LABEL_ASK).set(ask)
        gauge_bbo.labels(self.__site, product, _LABEL_BID).set(bid)

        mid = (ask + bid) * 0.5 if (ask is not None and bid is not None) else None
        gauge_mid.labels(self.__site, product).set(mid)

        ltp = tick['ltp'] if 'ltp' in tick else None
        gauge_ltp.labels(self.__site, product).set(ltp)


class CoincheckThread(threading.Thread):
    __site = 'coincheck'
    __target_addr = os.getenv('coincheck_addr', 'https://coincheck.com/api/ticker')
    __target_time = os.getenv('coincheck_time', 15)

    def run(self):

        while True:

            try:

                self.fetch('btc_jpy', _BBO_JPY_BTC, _MID_JPY_BTC, _LTP_JPY_BTC)

            except Exception as e:

                _logger.debug('%s : %s', type(e), e.args)

            time.sleep(self.__target_time)

    def fetch(self, product, gauge_bbo, gauge_mid, gauge_ltp):

        tick = requests.get(self.__target_addr).json()
        _logger.debug('[%s][%s] %s', self.__site, product, tick)

        ask = tick['ask'] if 'ask' in tick else None
        bid = tick['bid'] if 'bid' in tick else None
        gauge_bbo.labels(self.__site, product, _LABEL_ASK).set(ask)
        gauge_bbo.labels(self.__site, product, _LABEL_BID).set(bid)

        mid = (ask + bid) * 0.5 if (ask is not None and bid is not None) else None
        gauge_mid.labels(self.__site, product).set(mid)

        ltp = tick['last'] if 'last' in tick else None
        gauge_ltp.labels(self.__site, product).set(ltp)


class ZaifThread(threading.Thread):
    __site = 'zaif'
    __target_addr = os.getenv('zaif_addr', 'https://api.zaif.jp/api/1/ticker/')
    __target_time = os.getenv('zaif_time', 15)

    def run(self):

        while True:

            try:

                self.fetch('btc_jpy', _BBO_JPY_BTC, _MID_JPY_BTC, _LTP_JPY_BTC)

                self.fetch('bch_btc', _BBO_BTC_BCH, _MID_BTC_BCH, _LTP_BTC_BCH)

                self.fetch('eth_btc', _BBO_BTC_ETH, _MID_BTC_ETH, _LTP_BTC_ETH)

            except Exception as e:

                _logger.debug('%s : %s', type(e), e.args)

            time.sleep(self.__target_time)

    def fetch(self, product, gauge_bbo, gauge_mid, gauge_ltp):

        tick = requests.get(self.__target_addr + product).json()
        _logger.debug('[%s][%s] %s', self.__site, product, tick)

        ask = tick['ask'] if 'ask' in tick else None
        bid = tick['bid'] if 'bid' in tick else None
        gauge_bbo.labels(self.__site, product, _LABEL_ASK).set(ask)
        gauge_bbo.labels(self.__site, product, _LABEL_BID).set(bid)

        mid = (ask + bid) * 0.5 if (ask is not None and bid is not None) else None
        gauge_mid.labels(self.__site, product).set(mid)

        ltp = tick['last'] if 'last' in tick else None
        gauge_ltp.labels(self.__site, product).set(ltp)


class BitfinexThread(threading.Thread):
    __site = 'bitfinex'
    __target_addr = os.getenv('bitfinex_addr', 'https://api.bitfinex.com/v1/pubticker/')
    __target_time = os.getenv('bitfinex_time', 15)

    def run(self):

        while True:

            try:

                self.fetch('btcusd', _BBO_USD_BTC, _MID_USD_BTC, _LTP_USD_BTC)

                self.fetch('bchbtc', _BBO_BTC_BCH, _MID_BTC_BCH, _LTP_BTC_BCH)

                self.fetch('ethbtc', _BBO_BTC_ETH, _MID_BTC_ETH, _LTP_BTC_ETH)

            except Exception as e:

                _logger.debug('%s : %s', type(e), e.args)

            time.sleep(self.__target_time)

    def fetch(self, product, gauge_bbo, gauge_mid, gauge_ltp):

        tick = requests.get(self.__target_addr + product).json()
        _logger.debug('[%s][%s] %s', self.__site, product, tick)

        ask = float(tick['ask']) if 'ask' in tick else None
        bid = float(tick['bid']) if 'bid' in tick else None
        gauge_bbo.labels(self.__site, product, _LABEL_ASK).set(ask)
        gauge_bbo.labels(self.__site, product, _LABEL_BID).set(bid)

        mid = float(tick['mid']) if 'mid' in tick else None
        gauge_mid.labels(self.__site, product).set(mid)

        ltp = float(tick['last_price']) if 'last_price' in tick else None
        gauge_ltp.labels(self.__site, product).set(ltp)


class PoloniexThread(threading.Thread):
    __site = 'poloniex'
    __target_addr = os.getenv('poloniex_addr', 'https://poloniex.com/public?command=returnTicker')
    __target_time = os.getenv('poloniex_time', 15)

    def run(self):

        while True:

            try:

                json = requests.get(self.__target_addr).json()

                self.fetch(json, 'USDT_BTC', _BBO_USD_BTC, _MID_USD_BTC, _LTP_USD_BTC)

                self.fetch(json, 'BTC_BCH', _BBO_BTC_BCH, _MID_BTC_BCH, _LTP_BTC_BCH)

                self.fetch(json, 'BTC_ETH', _BBO_BTC_ETH, _MID_BTC_ETH, _LTP_BTC_ETH)

            except Exception as e:

                _logger.debug('%s : %s', type(e), e.args)

            time.sleep(self.__target_time)

    def fetch(self, json, product, gauge_bbo, gauge_mid, gauge_ltp):

        tick = json[product] if product in json else None
        _logger.debug('[%s][%s] %s', self.__site, product, tick)

        ask = float(tick['lowestAsk']) if 'lowestAsk' in tick else None
        bid = float(tick['highestBid']) if 'highestBid' in tick else None
        gauge_bbo.labels(self.__site, product, _LABEL_ASK).set(ask)
        gauge_bbo.labels(self.__site, product, _LABEL_BID).set(bid)

        mid = (ask + bid) * 0.5 if (ask is not None and bid is not None) else None
        gauge_mid.labels(self.__site, product).set(mid)

        ltp = float(tick['last']) if 'last' in tick else None
        gauge_ltp.labels(self.__site, product).set(ltp)


if __name__ == '__main__':
    # Start metrics server
    host = os.getenv('listen_port', 'localhost')
    port = os.getenv('listen_port', 10001)
    start_http_server(port, addr=host)

    # Start ticker threads
    BitflyerThread().start()
    CoincheckThread().start()
    ZaifThread().start()
    BitfinexThread().start()
    PoloniexThread().start()
