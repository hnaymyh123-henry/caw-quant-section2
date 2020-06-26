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

        self.smaf = bt.ind.MovingAverageSimple(period=self.params.pfast)
        self.smas = bt.ind.MovingAverageSimple(period=self.params.pslow)
        self.cross = bt.ind.CrossOver(self.smaf, self.smas)
        self.roc = bt.ind.RateOfChange()

        # To keep track of pending orders
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        self.order = None

    def next(self):

        if self.order:
            return

        if not self.position:
            if self.cross > 0:
                #self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()

        else:

            if self.cross < 0:

                #self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

    def stop(self):
        self.log('(fast Period %2d) (slow Period %2d) Ending Value %.2f' %
                 (self.params.pfast, self.params.pslow, self.broker.getvalue()))


if __name__ == '__main__':

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
    pfast_range = range(5, 21)
    strats = cerebro.optstrategy(
        SMACross, pfast=pfast_range, pslow=range(21, 50))

    # backtest setting
    cash = 10000
    cerebro.addsizer(bt.sizers.PercentSizer, percents=99)
    cerebro.broker.set_cash(cash)
    cerebro.broker.setcommission(commission=0.001)

    # add logger
    cerebro.addwriter(
        bt.WriterFile,
        out=os.path.join(logdir, 'log_SMAC_KPI.txt'),
        csv=True)

    cerebro.addanalyzer(bt.analyzers.Returns, _name='myreturn')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='mydrawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='mytrade')

    # run
    thestarts = cerebro.run()

    df = pd.DataFrame(columns=('periods_fast', 'periods_slow', 'end_value', 'return_ave', 'max_draw_downs', 'win_trades',
                              'loss_trades', 'total_trades', 'win_ratio', 'ave_win_value', 'ave_loss_value', 'ave_win_loss_ratio'), index=[0])

    for i in range(0, 450):

        periods_fast = thestarts[i][0].params.pfast
        periods_slow = thestarts[i][0].params.pslow

        returns = thestarts[i][0].analyzers.myreturn.get_analysis()
        return_ave = returns['ravg']

        drawdowns = thestarts[i][0].analyzers.mydrawdown.get_analysis()
        max_draw_downs = drawdowns['max']['drawdown']

        trades = thestarts[i][0].analyzers.mytrade.get_analysis()
        wintrades = trades['won']['total']
        losstrades = trades['lost']['total']

        totaltrades = wintrades + losstrades

        winratio = wintrades/totaltrades

        ave_win_value = trades['won']['pnl']['average']
        ave_loss_value = trades['lost']['pnl']['average']
        average_win_loss_ratio = ave_win_value/ave_loss_value

        total_pnl = trades['pnl']['net']['total']
        end_value = cash + int(total_pnl)

        data = pd.DataFrame({'periods_fast': periods_fast, 'periods_slow': periods_slow, 'end_value': end_value, 'return_ave': return_ave, 'max_draw_downs': max_draw_downs, 'win_trades': wintrades,
                           'loss_trades': losstrades, 'total_trades': totaltrades, 'win_ratio': winratio, 'ave_win_value': ave_win_value, 'ave_loss_value': ave_loss_value, 'ave_win_loss_ratio': average_win_loss_ratio}, index=[0])

        df = pd.concat([data, df], axis=0, ignore_index=True)
        
    df.to_csv('KPI_SMAC.csv')

    print(df.head())
    # Print out the final result
    #print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
