from typing import Tuple, Dict
import pandas as pd
from ftx.clients.rest_client import FtxAuth, FtxClient
from ftx.data._wranglers import preprocess_fills, preprocess_funding


_FILLS = ['fee', 'feeCurrency', 'feeRate', 'future', 'id', 'liquidity', 'market', 'baseCurrency', 'quoteCurrency',
                 ' orderId', 'tradeId', 'price', 'size', 'side', 'time', 'type'
                 ]

_FUNDING = ['future', 'id', 'payment', 'time']

_OPEN_POSITIONS = ['collateralUsed',	'cost',	'entryPrice',	'estimatedLiquidationPrice',	'future',	
                            'initialMarginRequirement',	'longOrderSize',	'maintenanceMarginRequirement',	'netSize',	
                            'openSize',	'realizedPnl',	'recentAverageOpenPrice',	'recentBreakEvenPrice',	'recentPnl',	
                            'shortOrderSize',	'side',	'size',	'unrealizedPnl'
                        ]


def fills_history(client: FtxClient) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    df = pd.DataFrame(client.get_all_fills())
    # Set proper format for empty dataframe if account has no history.
    if df.columns.empty:
        df = pd.DataFrame(columns=_FILLS)
    return preprocess_fills(df)

def funding_history(client: FtxClient) -> pd.DataFrame:
    df = pd.DataFrame(client.get_all_funding_payments())
    if df.columns.empty:
        df = pd.DataFrame(columns=_FUNDING)
    return preprocess_funding(df)

def open_positions(client: FtxClient, *args) -> pd.DataFrame:
    df = pd.DataFrame(client.get_positions(*args))
    if df.columns.empty:
        df = pd.DataFrame(columns=_OPEN_POSITIONS)
    return df