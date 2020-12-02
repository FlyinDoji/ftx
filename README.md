# FTX Exchange trade history tools

Includes a REST client for grabbing the full execution history from the platforms' API for any subaccount.
Provides several functions to process and extract a detailed trade history which includes paid fees, paid funding, trade duration and number of executions.

# Installation
Clone this repository
```
git clone https://github.com/FlyinDoji/ftx.git
```
Install the package with pip
```
pip install .
```

# Usage
After installation you can import the necessary libraries in your project or your notebook, see the sample notebook for an example. The client does not implement order placing or any operations that modify the account still, it is recommended to use a VIEW-ONLY API Key.
```
# Import client, fetchers and processors
from ftx.clients.rest_client import FtxAuth, FtxClient
from ftx.data.fetch import fills_history, funding_history, open_positions
from ftx.data.process import get_futures_summary, get_spot_summary, get_futures_trades_by_market
from tabulate import tabulate
import pandas as pd

pd.options.display.float_format = "{:,.2f}".format

key = 'YOUR-API-KEY'
secret = 'YOUR-API-SECRET'
auth = FtxAuth(key, secret, 'YOUR-SUBACCOUNT-NAME') # OR NONE IF MAIN ACCOUNT

c = FtxClient(auth)
# Full fill history
spot_fills, futures_fills, futures_by_market, spot_by_market = fills_history(c)
# Full funding payments history
funding = funding_history(c)
# Open positions
open_pos = open_positions(c)
```


# Futures trading summary of account
```
df = get_futures_summary(futures_fills, funding, open_pos)
print(tabulate(df, headers='keys', tablefmt='psql'))
```
```
+-----------+------------------+---------------+---------------+--------------+-------------+----------+-----------+----------+-----------+
|           |           Volume |   TakerVolume |   MakerVolume |   SellVolume |   BuyVolume |     Fees |   Funding |   RawPNL |      RPNL |
|-----------+------------------+---------------+---------------+--------------+-------------+----------+-----------+----------+-----------|
| BTC-PERP  | 592157           |     419949    |     172208    |    296861    |   295295    | 287.086  |  -47.8384 |  1565.99 | 1326.74   |
| ETH-PERP  | 417898           |     355801    |      62097.8  |    210981    |   206917    | 238.472  |  482.743  |  4064.46 | 3343.24   |
| PAXG-PERP |  18951.8         |      18540.6  |        411.25 |      9489.33 |     9462.51 |  12.4076 |   48.9459 |    26.82 |  -34.5335 |
| AMPL-PERP |    177.33        |        177.33 |          0    |        98.88 |       78.46 |   0.1179 |  -11.27   |    20.42 |   31.5721 |
| SOL-PERP  |  13873.8         |      11357.8  |       2516    |      6965.66 |     6908.12 |   7.5529 |    5.762  |    57.54 |   44.2251 |
| DOT-PERP  |  14752.9         |       5417.27 |       9335.58 |      7633.85 |     7119    |   3.6025 |   24.6309 |   514.85 |  486.617  |
| UNI-PERP  |   2550.66        |       1250.66 |       1300    |      1250.66 |     1300    |   0.8317 |    0      |   -49.34 |  -50.1717 |
| TOTAL     |      1.06036e+06 |     812493    |     247869    |    533281    |   527081    | 550.071  |  502.974  |  6200.74 | 5147.7    |
+-----------+------------------+---------------+---------------+--------------+-------------+----------+-----------+----------+-----------+
```
# Spot trading summary
```
df = get_spot_summary(spot_fills)
print(tabulate(df, headers='keys', tablefmt='psql'))
```
```
+---------+----------+---------------+---------------+--------------+-------------+---------+---------------+
|         |   Volume |   TakerVolume |   MakerVolume |   SellVolume |   BuyVolume |    Fees | FeeCurrency   |
|---------+----------+---------------+---------------+--------------+-------------+---------+---------------|
| FTT/USD |  5718.52 |        466.05 |       5252.47 |      4233    |     1485.52 |  0.3137 | USD           |
| ETH/USD | 24641    |      18701.4  |       5939.66 |     12750.7  |    11890.3  | 13.4329 | USD           |
| BTC/USD | 27827.8  |       7140.44 |      20687.4  |      6973.79 |    20854    |  5.5154 | USD           |
| BNB/USD |    92.5  |         92.5  |          0    |        46.12 |       46.38 |  0.0615 | USD           |
| MTA/USD |   602.74 |        602.74 |          0    |         0    |      602.74 |  0.4008 | USD           |
| ETH/BTC |     1.05 |          0.09 |          0.95 |         0.02 |        1.03 |  0.0001 | BTC           |
| FTT/BTC |     0.12 |          0.12 |          0    |         0.12 |        0    |  0.0001 | BTC           |
+---------+----------+---------------+---------------+--------------+-------------+---------+---------------+
```
# Futures trading history with each individual trade in a detailed layout
```
tm = get_futures_trades_by_market(futures_by_market, funding)
print(tabulate(tm['BTC-PERP'],headers='keys',))
```
```
  trade_nr         raw_pnl       fee       funding        rpnl    executions    volume  start                             end                               duration
----------  --------------  --------  ------------  ----------  ------------  --------  --------------------------------  --------------------------------  -----------------------
         0    25.75         10.3637    -10.9072       26.2936              2  14805.2   2019-12-06 14:31:02.152409+00:00  2019-12-09 16:51:39.854723+00:00  3 days 02:20:37.702314
         1   -82             9.97045    -0.310575    -91.6599              2  14243.5   2019-12-18 22:25:26.177956+00:00  2019-12-19 08:53:15.168636+00:00  0 days 10:27:48.990680
         2   429.792         3.59837    16.5168      409.677               8   7851.2   2019-12-24 16:18:49.527975+00:00  2020-01-13 09:47:16.137739+00:00  19 days 17:28:26.609764
         3   -18.1075        3.17383    11.4967      -32.778              15   6049.91  2020-02-15 14:26:13.652241+00:00  2020-02-19 21:33:09.279401+00:00  4 days 07:06:55.627160
         4  1921.67         32.848    -101.461      1990.28              171  58865.5   2020-02-21 17:02:41.305298+00:00  2020-05-10 00:17:25.576630+00:00  78 days 07:14:44.271332
         5    94.03          3.54623     0.909439     89.5743              3   8243.03  2020-05-10 00:20:54.388713+00:00  2020-05-10 16:59:07.757935+00:00  0 days 16:38:13.369222
         6    18.4467       11.6427     -0.932289      7.73634            10  17507.7   2020-05-11 10:16:42.492575+00:00  2020-05-11 16:38:34.053251+00:00  0 days 06:21:51.560676
         7  -253.99         12.6423      8.09154    -274.723               3  19011     2020-05-18 12:28:26.977734+00:00  2020-05-20 15:50:32.728793+00:00  2 days 03:22:05.751059
         8    54.7655        2.51229    -0.381456     52.6347              4   5846.27  2020-05-27 09:43:39.137333+00:00  2020-05-27 21:55:53.047591+00:00  0 days 12:12:13.910258
         9   -74             4.02487     1.0174      -79.0423              2   9456     2020-05-28 23:37:40.558849+00:00  2020-05-29 10:53:09.581689+00:00  0 days 11:15:29.022840
        10   -45.55         11.4922      3.26768     -60.3099             13  19365.6   2020-06-02 17:44:12.954373+00:00  2020-06-05 21:54:00.636061+00:00  3 days 04:09:47.681688
        11  -234.684         6.37971     0.865331   -241.929              11   9593.54  2020-06-11 07:03:48.742096+00:00  2020-06-11 16:52:03.340205+00:00  0 days 09:48:14.598109
        12     9.09495e-13   6.19946    -0.878555     -5.32091             4   9322.5   2020-06-19 16:47:20.218963+00:00  2020-06-20 20:33:47.425308+00:00  1 days 03:46:27.206345
        13   -38.6668        6.04866    -0.04561     -44.6698              9   9095.73  2020-06-29 15:06:38.194686+00:00  2020-06-29 16:09:13.755646+00:00  0 days 01:02:35.560960
        14     3.75          6.15408    -0.0461525    -2.35792             3   9254.25  2020-07-13 19:23:23.086626+00:00  2020-07-13 20:53:58.938281+00:00  0 days 01:30:35.851655
        15    43.0212        5.6758     -0.172121     37.5175              7   9945.32  2020-07-26 12:18:03.595879+00:00  2020-07-26 13:12:02.603522+00:00  0 days 00:53:59.007643
```