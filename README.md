# Kryptosekken-Elrond
A python script which creates a .csv file of all Elrond transactions, which can be imported into Kryptosekken.

## Use
Add your crypto wallet address, and run the script.

Correct earnings. The script doesn't know if received tokens are from f. ex. Binance/Crypto.com, or if they are a gift from someone. By default, all incoming tokens are treated as Overføring-Inn.

LKMEX is a bit special in the crypto world, since it's locked and you cannot exchange it in the next couple of years. The script allows you to turn on true_LKMEX_values if you want the value of LKMEX = MEX. If you set this function off 1.000.000 LKMEX = 1 NOK.

The script keeps a track of how much crypto is in your wallet. If 1 of these crypto becomes negative the script will stop and show an error message. If you want to ignore this error message you can set stop_when_negative = False. The error message will still appear, but the script wil continue making a .csv file.
