# -*- coding: utf-8 -*-
"""
Created on Wed Apr 27 21:27:00 2022

@author: Jessendelft
"""

import requests
import csv
import datetime
import json

wallet_address = ""
CoinAPI_key = ""

# CSV file:
# Tidspunkt,Type,Inn,Inn-Valuta,Ut,Ut-Valuta,Gebyr,Gebyr-Valuta,Marked,Notat
# 2017-05-17 12:00:00,Handel,1,BTC,15300,NOK,0,,coinbase,mitt første kjøp
# 2017-12-10 14:15:00,Handel,3822,EUR,0.3,BTC,57.33,EUR,coinbase,
# 2017-12-10 14:20:00,Mining,0.001,BTC,,,,,,mining

# TYPE
# Handel
# Erverv
# Mining
# Inntekt
# Renteinntekt
# Tap
# Forbruk
# Overføring-Inn
# Overføring-Ut
# Gave-Inn
# Gave-Ut
# Tap-uten-fradrag

#For testing purposes, we can keep track of our eGLD in the script.
egld = 0
stakedegld = 0
ESDTs = {}
timestamp = 0
csvwriter = 0
csverrorwriter = 0
transactionid = 0
gebyrValuta = "EGLD"
marked = "Elrond"
MexPrice = {}
RidePrice = {}

def writetx(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat = "", ):
    global timestamp, csvwriter, csverrorwriter, transactionid, gebyrValuta, \
        marked, MexPrice, RidePrice
    # Tidspunkt,Type,Inn,Inn-Valuta,Ut,Ut-Valuta,Gebyr,Gebyr-Valuta,Marked,Notat
    NormalWrite = True
    try:    InnValuta = InnValuta.split("-")[0]
    except: pass
    try:    UtValuta = UtValuta.split("-")[0]
    except: pass
    if (InnValuta == "MEX" or InnValuta == "LKMEX" or InnValuta == "RIDE") and \
        Ut == 0 and Type == "Inntekt":
        epoch = timestamp.isoformat()
        UtValuta = "NOK"
        if epoch in MexPrice:
            Ut = MexPrice[epoch]
        elif epoch in RidePrice:
            Ut = RidePrice[epoch]
        else:
            if InnValuta == "LKMEX":
                url = 'https://rest.coinapi.io/v1/exchangerate/MEX/NOK?time=' + str(epoch)
            else:
                url = 'https://rest.coinapi.io/v1/exchangerate/' + InnValuta + '/NOK?time=' + str(epoch)
            print(url)
            headers = {'X-CoinAPI-Key' : CoinAPI_key}
            response = requests.get(url, headers=headers)
            responsejson = response.json()
            print(responsejson)
            try:
                Ut = float(responsejson["rate"]) * float(10**18)
                if InnValuta == "MEX" or InnValuta == "LKMEX":
                    MexPrice[epoch] = Ut
                elif InnValuta == "RIDE":
                    RidePrice[epoch] = Ut
            except KeyError:
                NormalWrite = False
    if NormalWrite:
        csvwriter.writerow([timestamp, \
                            Type, \
                            str(float(Inn)/float(10**18)), \
                            InnValuta, \
                            str(float(Ut)/float(10**18)), \
                            UtValuta, \
                            str(float(Gebyr)/float(10**18)), \
                            gebyrValuta, \
                            marked, \
                            "Hash: " + transactionid + ". " + Notat])
    else:
        csverrorwriter.writerow([timestamp, \
                            Type, \
                            str(float(Inn)/float(10**18)), \
                            InnValuta, \
                            str(float(Ut)/float(10**18)), \
                            UtValuta, \
                            str(float(Gebyr)/float(10**18)), \
                            gebyrValuta, \
                            marked, \
                            "Hash: " + transactionid + ". " + Notat])

def csvparser():
    global egld, stakedegld, ESDTs, timestamp, \
        csvwriter, csverrorwriter, transactionid, gebyrValuta, marked, \
            MexPrice, RidePrice
    url = "https://api.elrond.com/accounts/" + wallet_address + \
        "/transactions?size=1000&before=1640991600&after=1609455600&withLogs=false"
    transactions = requests.get(url).json()
    with open('Elrond_Transactions.csv', 'w', newline='') as csvfile, \
            open('Elrond_Missing_Valuta.csv', 'w', newline='') as errorfile, \
                open("mexprices.json", "a") as mexprices, \
                    open("rideprices.json", "a") as rideprices:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csverrorwriter = csv.writer(errorfile, delimiter=',')
        csvwriter.writerow(["Tidspunkt","Type","Inn","Inn-Valuta","Ut",
                           "Ut-Valuta","Gebyr","Gebyr-Valuta","Marked","Notat"])
        csverrorwriter.writerow(["Tidspunkt","Type","Inn","Inn-Valuta","Ut",
                           "Ut-Valuta","Gebyr","Gebyr-Valuta","Marked","Notat"])
        try:        MexPrice = json.load(mexprices)
        except :    pass
        try:        RidePrice = json.load(rideprices)
        except :    pass
        # Now the main loop starts
        for transaction in reversed(transactions):
            fee = int(transaction["fee"])
            timestamp = datetime.datetime.fromtimestamp(transaction["timestamp"])
            transactionid = transaction["txHash"]
            egld = egld - fee
            # First, check if the transaction actually succeeded.
            if transaction["status"] != "success":
                writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "failed")
            elif transaction["sender"] == wallet_address:
                # Try to read the action field.
                if "action" in transaction:
                    name = transaction["action"]["name"]
                    # Delegating
                    if name == "delegate":
                        eGLDvalue = int(transaction["value"])
                        stakedegld += eGLDvalue
                        egld -= eGLDvalue
                        writetx("Overføring-Ut", 0, "", eGLDvalue, "EGLD", fee, name)
                    # unDelegating
                    elif name == "unDelegate":
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, name)
                        #Nothing of interest happens here, funds are not returned until withdraw
                    # unBond (legacy) or withdraw
                    elif name == "unBond" or name == "withdraw":
                        fulltx = requests.get("https://api.elrond.com/transactions/"+transactionid)
                        fulltxjson = fulltx.json()
                        for result in fulltxjson["results"]:
                            if result["receiver"] == wallet_address:
                                eGLDvalue = int(result["value"])
                                stakedegld -= eGLDvalue
                                egld += eGLDvalue
                                writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", 0, name)
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                    # Staking (legacy)
                    elif name == "stake":
                        eGLDvalue = int(transaction["value"])
                        stakedegld += eGLDvalue
                        egld -= eGLDvalue
                        writetx("Overføring-Ut", 0, "", eGLDvalue, "EGLD", fee, name)
                    # unStaking (legacy)
                    elif name == "unStake":
                        fulltx = requests.get("https://api.elrond.com/transactions/"+transactionid)
                        fulltxjson = fulltx.json()
                        for result in fulltxjson["results"]:
                            if fulltxjson["receiver"] == wallet_address:
                                eGLDvalue = int(result["value"])
                                egld += eGLDvalue
                                writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", 0, name)
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                    # reDelegating
                    elif name == "reDelegateRewards":
                        fulltx = requests.get("https://api.elrond.com/transactions/"+transactionid)
                        fulltxjson = fulltx.json()
                        for result in fulltxjson["results"]:
                            if result["receiver"] == wallet_address:
                                eGLDvalue = int(result["value"])
                                stakedegld += eGLDvalue
                                writetx("Inntekt", eGLDvalue, "EGLD", 0, "EGLD", 0, name)
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                    # wrapEGLD == handel
                    elif name == "wrapEgld":
                        eGLDvalue = int(transaction["action"]["arguments"]["token"]["value"])
                        ticker = transaction["action"]["arguments"]["token"]["ticker"]
                        total = 0
                        if ticker in ESDTs.keys():
                            total = ESDTs.get(ticker)
                        egld -= eGLDvalue
                        ESDTs[ticker] = total + eGLDvalue
                        writetx("Handel", eGLDvalue, ticker, eGLDvalue, "EGLD", fee, name)
                    # unwrapEgld == handel
                    elif name == "unwrapEgld":
                        for transfer in transaction["action"]["arguments"]["transfers"]:
                            eGLDvalue = int(transfer["value"])
                            ticker = transfer["ticker"]
                            total = 0
                            if ticker in ESDTs.keys():
                                total = ESDTs.get(ticker)
                            egld += eGLDvalue
                            ESDTs[ticker] = total - eGLDvalue
                            writetx("Handel", eGLDvalue, "EGLD", eGLDvalue, ticker, 0, name)
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                    # claim first LKMEX batch == inntekt
                    elif name == "claimLockedAssets":
                        fulltx = requests.get("https://api.elrond.com/transactions/"+transactionid)
                        fulltxjson = fulltx.json()
                        for operation in fulltxjson["operations"]:
                            if operation["action"] == "transfer":
                                ticker = "LKMEX"
                                total = 0
                                ESDTvalue = int(operation["value"])
                                if ticker in ESDTs.keys():
                                    total = ESDTs.get(ticker)
                                ESDTs[ticker] = total + ESDTvalue
                                writetx("Inntekt", ESDTvalue, ticker, 0, "EGLD", 0, name)
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                    # confirm our Tickets
                    elif name == "confirmTickets":
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                    # claim Launchpad tokens. Claim == inntekt
                    elif name == "claimLaunchpadTokens":
                        fulltx = requests.get("https://api.elrond.com/transactions/"+transactionid)
                        fulltxjson = fulltx.json()
                        for operation in fulltxjson["operations"]:
                            if operation["type"] == "egld":
                                total = 0
                                eGLDvalue = int(operation["value"])
                                egld += eGLDvalue
                                writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "EGLD", 0, name)
                            elif operation["type"] == "esdt":
                                ticker = "RIDE"
                                total = 0
                                ESDTvalue = int(operation["value"])
                                if ticker in ESDTs.keys():
                                    total = ESDTs.get(ticker)
                                ESDTs[ticker] = total + ESDTvalue
                                writetx("Handel", ESDTvalue, ticker, (ESDTvalue / 5000) * 0.47, "EGLD", 0, name)
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                    # compoundRewards. When we're compounding, we need to look at the difference.
                    # Everything else
                    else:
                        fulltx = requests.get("https://api.elrond.com/transactions/"+transactionid)
                        fulltxjson = fulltx.json()
                        Tokenssent = {}
                        Tokensreceived = {}
                        # Check what we've received.
                        for operation in fulltxjson["operations"]:
                            if operation["action"] == "transfer":
                                try:
                                    ticker = operation["identifier"].split("-")[0]
                                    tickerkey = operation["identifier"]
                                except KeyError:
                                    ticker = "EGLD"
                                ESDTvalue = int(operation["value"])
                                total = 0
                                if ticker in ESDTs.keys():
                                    total = ESDTs.get(ticker)
                                if operation["receiver"] == wallet_address and \
                                   ticker != "EGLD":
                                    total += ESDTvalue
                                    Tokensreceived[tickerkey] = ESDTvalue
                                elif operation["receiver"] == wallet_address:
                                    egld += ESDTvalue
                                    Tokensreceived[ticker] = ESDTvalue
                                if operation["sender"] == wallet_address:
                                    total -= ESDTvalue
                                    Tokenssent[tickerkey] = ESDTvalue
                                ESDTs[ticker] = total
                        if name == "addLiquidity":
                            mainticker = list(Tokensreceived.keys())[0]
                            if mainticker in Tokenssent.keys():
                                Tokensreceived[mainticker] = \
                                    Tokensreceived[mainticker] - Tokenssent[mainticker]
                                del Tokenssent[mainticker]
                            for key in Tokenssent.keys():
                                writetx("Handel", Tokensreceived[mainticker] / len(Tokenssent.keys()), 
                                        mainticker, Tokenssent[key], key, 
                                        fee / len(Tokenssent.keys()), 
                                        name + ". Double check these numbers!")
                            del Tokensreceived[mainticker]
                            for key in Tokensreceived.keys():
                                writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
                        elif name == "removeLiquidity":
                            mainticker = list(Tokenssent.keys())[0]
                            for key in Tokensreceived.keys():
                                writetx("Handel", Tokensreceived[key], key,
                                        Tokenssent[mainticker] / len(Tokenssent.keys()),
                                        mainticker, fee / len(Tokensreceived.keys()),
                                        name + ". Double check these numbers!")
                            del Tokenssent[mainticker]
                            for key in Tokenssent.keys():
                                writetx("Erverv", Tokenssent[key], key, 0, "", 0, name)
                        elif name == "enterFarm" or name == "compoundRewards":
                            for key in Tokenssent.keys():
                                if key in Tokensreceived.keys():
                                    difference = Tokensreceived[key] - Tokenssent[key]
                                    del Tokensreceived[key]
                                    writetx("Erverv", difference, key, 0, "", 0, name)
                                else:
                                    writetx("Tap-uten-fradrag", 0, "", Tokenssent[key], key, 0, name)
                            for key in Tokensreceived.keys():
                                writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
                            writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                        elif name == "exitFarm":
                            for key in Tokenssent.keys():
                                if key in Tokensreceived.keys():
                                    difference = Tokenssent[key] - Tokensreceived[key]
                                    del Tokensreceived[key]
                                    writetx("Tap-uten-fradrag", 0, "", difference, key, 0, name)
                                else:
                                    writetx("Tap-uten-fradrag", 0, "", Tokenssent[key], key, 0, name)
                            for key in Tokensreceived.keys():
                                if key.split("-")[0] == "MEX" or \
                                    key.split("-")[0] == "LKMEX" and \
                                        len(Tokensreceived.keys()) > 2:
                                    writetx("Inntekt", Tokensreceived[key], key, 0, "", 0, name)
                                else:
                                    writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
                            writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                        elif name == "mergeLockedAssetTokens":
                            writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, name + " fee")
                        elif name == "swap":
                            swapout = transaction["action"]["arguments"]["transfers"][0]["token"]
                            swapin = transaction["action"]["arguments"]["transfers"][1]["token"]
                            writetx("Handel", Tokensreceived[swapin], swapin, \
                                    Tokenssent[swapout], swapout, fee, name)
                            del Tokensreceived[swapin]
                            del Tokenssent[swapout]
                            for key in Tokenssent.keys():
                                writetx("Inntekt", Tokenssent[key], key, 0, "", 0, name)
                            for key in Tokensreceived.keys():
                                writetx("Inntekt", Tokensreceived[key], key, 0, "", 0, name)
                        elif name == "claimRewards":
                            for key in Tokenssent.keys():
                                if key in Tokensreceived:
                                    difference = Tokenssent[key] - Tokensreceived[key]
                                    del Tokensreceived[key]
                                    if difference > 0:
                                        writetx("Tap-uten-fradrag", 0, "", difference, key, 0, name)
                                else:
                                    writetx("Overføring-Ut", 0, "", Tokenssent[key], key, 0, name)
                            for key in Tokensreceived.keys():
                                writetx("Inntekt", Tokensreceived[key], key, 0, "", 0, name)
                            writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                #if no action, it's just a regular transfer out:
                else:
                    eGLDvalue = int(transaction["value"])
                    egld = egld - eGLDvalue
                    writetx("Overføring-Ut", 0, "", eGLDvalue, "EGLD", fee,\
                            "Regular transfer out. Double check this type!")
            # Check if we're receiving something, and if yes, what it is
            elif transaction["receiver"] == wallet_address:
                # Try to read the action field.
                if "action" in transaction:
                    for transfer in transaction["action"]["arguments"]["transfers"]:
                        total = 0
                        ESDTvalue = int(transfer["value"])
                        ticker = transfer["ticker"].split("-")[0]
                        if ticker in ESDTs.keys():
                            total = ESDTs.get(ticker)
                        ESDTs[ticker] = total + ESDTvalue
                        writetx("Overføring-Inn", ESDTvalue, ticker, 0, "", 0, \
                                "Regular transfer in. Double check this type!")
                    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                else:
                    eGLDvalue = int(transaction["value"])
                    egld = egld + eGLDvalue
                    writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", fee,
                            "Regular transfer in. Double check this type!")
            else:
                print("unknown")
                print(transactionid)
            stop = False
            for key in ESDTs:
                if ESDTs[key] < -1*(10**18):
                    print(transactionid)
                    stop = True
            if stop: break
            if egld < 0:
                print(transactionid)
                break
            try:
                print(timestamp.isoformat() + " LKMEX: " + str(ESDTs["LKMEX"]/float(10**18)) + " " + name)
            except KeyError:
                pass
        mexprices.write(json.dumps(MexPrice))
        rideprices.write(json.dumps(RidePrice))
        print("EGLD :" + str(float(egld)/float(10**18)) + \
              ". Staked: " + str(float(stakedegld)/float(10**18)) + \
                  ". Hash:" + transactionid)
        for ESDT in ESDTs:    
            print(ESDT + ": " + str(float(ESDTs[ESDT])/float(10**18)))

if __name__ == "__main__":
    csvparser()