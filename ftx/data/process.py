import pandas as pd
import numpy as np
from ftx.clients.rest_client import FtxAuth, FtxClient
from ftx.data._wranglers import add_trades, preprocess_fills


# Account summary for all traded futures
def get_futures_summary(futures_fills: pd.DataFrame, funding: pd.DataFrame, open_positions: pd.DataFrame) -> pd.DataFrame:

    active_markets = futures_fills['market'].unique()
    futures_summary = pd.DataFrame(columns=['Volume', 'TakerVolume', 'MakerVolume', 'SellVolume', 'BuyVolume', 'Fees', 'Funding'])

    for market in active_markets:
        active_market_df = futures_fills[futures_fills['market'] == market]
        # Subtract any open shorts from the total sold value
        open_short_value = (lambda x: np.float(0) if x.empty else np.float(x))(np.minimum(open_positions[open_positions['future'] == market]['cost'], 0))
        # Subtract any open longs from the total bought value
        open_long_value = (lambda x: np.float(0) if x.empty else np.float(x))(np.maximum(open_positions[open_positions['future'] == market]['cost'], 0))

        market_summary = pd.Series(
            {
                "Volume": active_market_df['volume'].sum().round(2),
                "TakerVolume": active_market_df[active_market_df['liquidity'] == 'taker']['volume'].sum().round(2),
                "MakerVolume": active_market_df[active_market_df['liquidity'] == 'maker']['volume'].sum().round(2),
                "SellVolume": active_market_df[active_market_df['side'] == 'sell']['volume'].sum().round(2) + open_short_value,
                "BuyVolume": active_market_df[active_market_df['side'] == 'buy']['volume'].sum().round(2) - open_long_value,
                "Fees": active_market_df['fee'].sum().round(4),
                "Funding": funding[funding['future'] == market]['payment'].sum().round(4)
            },
            name=market)

        futures_summary = futures_summary.append(market_summary)

    cummulative = pd.Series(
        {
            "Volume": futures_summary['Volume'].sum(),
            "TakerVolume": futures_summary['TakerVolume'].sum(),
            "MakerVolume": futures_summary['MakerVolume'].sum(),
            "SellVolume": futures_summary['SellVolume'].sum(),
            "BuyVolume": futures_summary['BuyVolume'].sum(),
            "Fees": futures_summary['Fees'].sum(),
            "Funding": futures_summary['Funding'].sum()
        },
        name="TOTAL")
    futures_summary = futures_summary.append(cummulative)
    futures_summary['RawPNL'] = futures_summary['SellVolume'] - futures_summary['BuyVolume']
    futures_summary['RPNL'] = futures_summary['RawPNL'] - futures_summary['Fees'] - futures_summary['Funding']

    return futures_summary


# Account summary for all traded spot markets
def get_spot_summary(spot_fills: pd.DataFrame) -> pd.DataFrame:

    active_markets = spot_fills['market'].unique()
    spot_summary = pd.DataFrame(columns=[
        'Volume',
        'TakerVolume',
        'MakerVolume',
        'SellVolume',
        'BuyVolume',
        'Fees',
    ])

    for market in active_markets:
        active_market_df = spot_fills[spot_fills['market'] == market]
        fee_currency = market.split('/')[1]
        market_summary = pd.Series(
            {
                "Volume": active_market_df['volume'].sum().round(2),
                "TakerVolume": active_market_df[active_market_df['liquidity'] == 'taker']['volume'].sum().round(2),
                "MakerVolume": active_market_df[active_market_df['liquidity'] == 'maker']['volume'].sum().round(2),
                "SellVolume": active_market_df[active_market_df['side'] == 'sell']['volume'].sum().round(2),
                "BuyVolume": active_market_df[active_market_df['side'] == 'buy']['volume'].sum().round(2),
                # Use the quote currency as the fee currency ie ETH/BTC fees are denominated in BTC
                # Convert fees from fee currency to quote currency where needed
                "Fees": active_market_df.apply(lambda row: row.fee * row.price if row.feeCurrency != fee_currency else row.fee, axis=1).sum().round(4),
                "FeeCurrency": fee_currency,
            },
            name=market)

        spot_summary = spot_summary.append(market_summary)
        active_market_df.apply(lambda row: row.fee * row.price if row.feeCurrency != fee_currency else row.fee, axis=1)

    return spot_summary


# Trades that are not closed will not be shown
def get_futures_trades_by_market(fills_by_market: pd.DataFrame, funding: pd.DataFrame) -> pd.DataFrame:
    fills_by_market = {market: add_trades(df) for market, df in fills_by_market.items()}
    trades_by_market = {}
    for future, df in fills_by_market.items():

        volume = df.groupby('trade_nr')['volume'].sum()
        fees = df.groupby('trade_nr')['fee'].sum()
        value = df.groupby(['trade_nr', 'side'])['volume'].sum()
        raw_pnl = value.groupby('trade_nr').diff().droplevel('side').dropna()
        raw_pnl.name = 'raw_pnl'
        start_time = df.groupby('trade_nr')['time'].min()
        start_time.name = 'start'
        end_time = df.groupby('trade_nr')['time'].max()
        end_time.name = 'end'
        duration = end_time - start_time
        duration.name = 'duration'
        executions = df.groupby('trade_nr')['time'].count()
        executions.name = 'executions'

        f = funding[funding['future'] == df['market'].iloc[0]].copy()
        f = f.set_index('time').sort_index()

        trades = pd.concat([
            raw_pnl,
            fees,
            volume,
            executions,
            start_time,
            end_time,
            duration,
        ], axis=1)
        trades['funding'] = trades.apply(lambda x: f['payment'][x.start:x.end].sum(), axis=1)
        trades['rpnl'] = trades['raw_pnl'] - trades['fee'] - trades['funding']
        trades = trades[[
            'raw_pnl',
            'fee',
            'funding',
            'rpnl',
            'executions',
            'volume',
            'start',
            'end',
            'duration',
        ]]

        # Delete last trade if position still open
        if df.iloc[-1]['delta'] != 0:
            trades.drop(df.iloc[-1]['trade_nr'], inplace=True)

        trades_by_market[future] = trades

    return trades_by_market