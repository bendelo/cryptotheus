#!/usr/bin/env python

import cryptotheus


def main():
    context = cryptotheus.Context()
    context.launch_server()

    cryptotheus.BitfinexTicker(context).start()
    cryptotheus.BitflyerTicker(context).start()
    cryptotheus.CoincheckTicker(context).start()
    cryptotheus.OandaTicker(context).start()
    cryptotheus.PoloniexTicker(context).start()
    cryptotheus.ZaifTicker(context).start()


if __name__ == '__main__':
    main()
