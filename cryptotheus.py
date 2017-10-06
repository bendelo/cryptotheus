#!/usr/bin/env python

import cryptotheus


def main():
    context = cryptotheus.TickerContext()
    context.launch_server()

    cryptotheus.BitfinexThread(context).start()
    cryptotheus.BitflyerThread(context).start()
    cryptotheus.CoincheckThread(context).start()
    cryptotheus.PoloniexThread(context).start()
    cryptotheus.ZaifThread(context).start()


if __name__ == '__main__':
    main()
