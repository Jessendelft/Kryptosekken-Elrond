# Kryptosekken-Elrond
A python script which creates a .csv file of all Elrond transactions, which can be imported into Kryptosekken.

## Use
Apply for a free CoinAPI API Key at https://www.coinapi.io/ to allow retrieval of MEX, LKMEX and RIDE price data.
Update the wallet_address and CoinAPI_key in the python script.
Make sure to wait at least 10 minutes between applying for the CoinAPI key and running the script with the new key.

Now run the script.
All transactions are written to Elrond_Transactions.csv. Any transaction which fails the CoinAPI call is put in a seperate file called Elrond_Missing_Valuta.csv.
You will need to update the NOK value of each trade in here manually before uploading both files to the Kryptosekken manual file upload: https://www.kryptosekken.no/regnskap/importer-csv-generisk2
