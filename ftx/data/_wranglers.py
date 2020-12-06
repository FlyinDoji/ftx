from decimal import Decimal, getcontext
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import ftx.data._precisions as prec

getcontext().prec = 6


def decimal_with_precision(x: str, precision: int) -> Decimal:
    return round(Decimal(x), precision)


def convert_futures_size(futures_fills: pd.DataFrame) -> pd.DataFrame:
    futures_fills.loc[:, 'size'] = futures_fills.loc[:, ['size']].astype('str')
    for mkt in futures_fills['market'].unique():
        mkt = mkt.split('-')[0]

        # Will error if there is no entry in the Precisions Dict.
        futures_fills.loc[futures_fills['market'].str.contains(mkt), 'size'] = futures_fills.loc[futures_fills['market'].str.contains(mkt), 'size'].apply(decimal_with_precision, args=(prec.FUTURES_SIZE[mkt], ))
    return futures_fills


def convert_futures_price(futures_fills: pd.DataFrame) -> pd.DataFrame:
    futures_fills.loc[:, 'price'] = futures_fills.loc[:, ['price']].astype('str')
    for mkt in futures_fills['market'].unique():
        mkt = mkt.split('-')[0]
        futures_fills.loc[futures_fills['market'].str.contains(mkt), 'price'] = futures_fills.loc[futures_fills['market'].str.contains(mkt), 'price'].apply(decimal_with_precision, args=(prec.FUTURES_PRICE[mkt], ))
    return futures_fills


def convert_futures_fee(futures_fills: pd.DataFrame) -> pd.DataFrame:
    futures_fills.loc[:, 'fee'] = futures_fills.loc[:, ['fee']].astype('str')
    for mkt in futures_fills['market'].unique():
        mkt = mkt.split('-')[0]
        futures_fills.loc[futures_fills['market'].str.contains(mkt), 'fee'] = futures_fills.loc[futures_fills['market'].str.contains(mkt), 'fee'].apply(decimal_with_precision, args=(prec.FUTURES_FEE, ))
    return futures_fills


def convert_futures_feeRate(futures_fills: pd.DataFrame) -> pd.DataFrame:
    futures_fills.loc[:, 'feeRate'] = futures_fills.loc[:, ['feeRate']].astype('str')
    futures_fills.loc[:, 'feeRate'] = futures_fills.loc[:, 'feeRate'].apply(decimal_with_precision, args=(prec.FUTURES_FEERATE, ))
    return futures_fills


def compute_deltas(fills: pd.DataFrame) -> pd.DataFrame:
    fills['size'] = fills['size'].mask(fills['side'] == 'sell', -fills['size'])
    fills['delta'] = fills['size'].cumsum()
    return fills


def preprocess_fills(fills: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:

    # Convert unique identifiers to string
    fills['id'] = fills['id'].astype('str')
    fills['orderId'] = fills['orderId'].astype('str')
    fills['tradeId'] = fills['tradeId'].astype('str')

    fills['time'] = pd.to_datetime(fills['time'])
    # Sort fills by time and id
    fills.sort_values(['time', 'id'], inplace=True, axis=0, ignore_index=True)
    # Add volume column
    fills['volume'] = fills['size'] * fills['price']

    # Split spot and futures
    spot = fills[(fills['future'].isnull()) & (fills['type'] != 'otc')].copy()
    futures = fills[fills['future'].notnull()].copy()

    # Drop unused columns in futures
    futures.drop('baseCurrency', axis=1, inplace=True)
    futures.drop('quoteCurrency', axis=1, inplace=True)

    # Convert size to Decimal
    futures = convert_futures_size(futures)

    # Split futures by market
    futures_by_market = {mkt: futures[futures['market'] == mkt].copy() for mkt in futures['market'].unique()}
    spot_by_market = {mkt: spot[spot['market'] == mkt].copy() for mkt in spot['market'].unique()}

    return spot, futures, futures_by_market, spot_by_market


def preprocess_funding(funding: pd.DataFrame) -> pd.DataFrame:

    # Convert time
    funding['time'] = pd.to_datetime(funding['time'])
    return funding


# Mark fills that belong to the same trade
# A trade starts when market delta is flipped from neutral (0) to long (+) or short (-)
# A fill that flips delta sign is considered to end one trade and open another, and it is split accordingly
def add_trades(fills: pd.DataFrame) -> pd.DataFrame:

    fills = compute_deltas(fills)

    # Mark fills that flipped the delta sign
    flip_counter = np.sign(fills['delta']) * np.sign(fills['delta'].shift().fillna(0))
    flip_counter[flip_counter > 0] = 0
    flip_counter = flip_counter.abs().astype('int') + 1

    # Duplicate rows where the fill needs to be split
    fills = fills.reindex(fills.index.repeat(flip_counter.values))
    # Same timestamp can appear for multiple fills, find duplicates by ID
    # Duplicates are in sets of 2, set flags for both occurences
    fills['split_fill'] = np.nan

    # keep='last' will consider the second fill to be the original and mark the first as the duplicate
    fills.loc[fills['id'].duplicated(keep='last'), 'split_fill'] = 'first'
    # keep='first' will consider the first fill to be the original and mark the second as the duplicate
    fills.loc[fills['id'].duplicated(keep='first'), 'split_fill'] = 'second'

    # preserve uniqueness of identifier columns, ID contains digits only so collisions are avoided
    fills.loc[fills['split_fill'] == 'second', 'orderId'] += 'b'
    fills.loc[fills['split_fill'] == 'second', 'tradeId'] += 'b'
    fills.loc[fills['split_fill'] == 'second', 'id'] += 'b'

    # Recompute split_fills accordingly
    # First
    fills.loc[fills['split_fill'] == 'first',
              'size'] = np.sign(fills.loc[fills['split_fill'] == 'first', 'size']) * (np.abs(fills.loc[fills['split_fill'] == 'first', 'size']) - np.abs(fills.loc[fills['split_fill'] == 'first', 'delta']))
    fills.loc[fills['split_fill'] == 'first', 'volume'] = np.abs(fills.loc[fills['split_fill'] == 'first', 'size'].astype('float')) * fills.loc[fills['split_fill'] == 'first', 'price']
    fills.loc[fills['split_fill'] == 'first', 'fee'] = fills.loc[fills['split_fill'] == 'first', 'volume'] * fills.loc[fills['split_fill'] == 'first', 'feeRate']
    fills.loc[fills['split_fill'] == 'first', 'delta'] = Decimal('0.0000')
    # Second
    fills.loc[fills['split_fill'] == 'second', 'size'] = fills.loc[fills['split_fill'] == 'second', 'delta']
    fills.loc[fills['split_fill'] == 'second', 'volume'] = np.abs(fills.loc[fills['split_fill'] == 'second', 'size'].astype('float')) * fills.loc[fills['split_fill'] == 'second', 'price']
    fills.loc[fills['split_fill'] == 'second', 'fee'] = fills.loc[fills['split_fill'] == 'second', 'volume'] * fills.loc[fills['split_fill'] == 'second', 'feeRate']

    # Mark fills belonging to the same trade
    fills['trade_nr'] = fills['delta'].shift().eq(0).cumsum()
    return fills
