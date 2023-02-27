# Kryptosekken-Elrond
A python script which creates a .csv file of all Elrond transactions, which can be imported into Kryptosekken.

## Use
Add your crypto wallet address, and run the script.

Correct earnings. The script doesn't know if received tokens are from f. ex. Binance/Crypto.com, or if they are a gift from someone. By default, all incoming tokens are treated as Overføring-Inn.

LKMEX is a bit special in the crypto world, since it's locked and you cannot exchange it in the next couple of years. The script allows you to turn on true_LKMEX_values if you want the value of LKMEX = MEX. If you set this function off 1.000.000 LKMEX = 1 NOK.

## Latest update: 27-02-2023
Update elrondparser.py
- Updated main function split & it into multiple subfunctions.
- Updated API address to new multiversx address.
- Removed internal token counter as it was broken anyway.
- Improved URL retrieval. Takes max 2 queries/ip/second.
- Added support for Aliases
- Added support for NFT's.
- Added support for NFT handel. NOTE: Does not work for handel done on eMoon unfortunately as their transactions don't include details of what has been sold.
- Partial XMEX support, but may be insufficient.
- Multiple small fixes.
Removed mexprices.json, rideprices.json, egldprices.json as they were unused.
