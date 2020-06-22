import os
import datetime

import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

import data_fetcher

datadir = './Data'  # data path
logdir = './Log'  # log path
reportdir = './Report'  # report path
datafile = 'BTC_USDT_1h.csv'  # data file
from_datetime = '2020-01-01 00:00:00'  # start time
to_datetime = '2020-04-01 00:00:00'  # end time


class SMACross(bt.Strategy):

    params = (
        ('pfast', 10),
        ('pslow', 20),
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        
        self.smaf = bt.ind.SmoothedMovingAverage(period=self.params.pfast)
        self.smas = bt.ind.SmoothedMovingAverage(period=self.params.pslow)
        self.cross = bt.ind.CrossOver(self.smaf, self.smas)
        self.roc = bt.ind.RateOfChange()

        # To keep track of pending orders
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def next(self):

        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return    

        # Check if we are in the market
        if not self.position:
            if self.cross > 0:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()

        else:

            if self.roc < -0.1:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

            
            else:
                if self.cross < 0:

                    self.log('SELL CREATE, %.2f' % self.dataclose[0])
                    self.order = self.sell()

                


        

if __name__ == '__main__':

    # initiate cerebro instance
    cerebro = bt.Cerebro()

    # feed data
    data = pd.read_csv(
        os.path.join(datadir, 'BTC_USDT_1h.csv'), index_col='datetime', parse_dates=True)
    data = data.loc[
        (data.index >= pd.to_datetime(from_datetime)) &
        (data.index <= pd.to_datetime(to_datetime))]
    datafeed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(datafeed)

    # feed strategy
    cerebro.addstrategy(SMACross)

    # backtest setting
    cerebro.addsizer(bt.sizers.PercentSizer, percents=99)
    cerebro.broker.set_cash(10000)
    cerebro.broker.setcommission(commission=0.001)

    # add logger
    cerebro.addwriter(
        bt.WriterFile,
        out=os.path.join(logdir, 'log.txt'),
        csv=True)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    #run
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    #save report
    plt.rcParams['figure.figsize'] = [13.8, 10]
    fig = cerebro.plot(style='candlestick', barup='green', bardown='red')
    fig[0][0].savefig(
	    os.path.join(reportdir, 'report.png'),
	    dpi=480)