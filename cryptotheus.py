#!/usr/bin/env python

import cryptotheus


def main():
    context = cryptotheus.Context()
    context.launch_server()

    cryptotheus.BitfinexTicker(context).start()
    cryptotheus.BitflyerTicker(context).start()
    cryptotheus.BitmexTicker(context).start()
    cryptotheus.CoincheckTicker(context).start()
    cryptotheus.OandaTicker(context).start()
    cryptotheus.PoloniexTicker(context).start()
    cryptotheus.QuoineTicker(context).start()
    cryptotheus.ZaifTicker(context).start()

    cryptotheus.BitflyerAccount(context).start()
    cryptotheus.BitmexAccount(context).start()


if __name__ == '__main__':
    main()
