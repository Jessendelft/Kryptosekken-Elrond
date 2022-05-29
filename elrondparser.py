# -*- coding: utf-8 -*-
"""
Created on Wed Apr 27 21:27:00 2022

@author: Jessendelft
"""

import requests
import csv
import datetime
import json
import time

wallet_address = ""

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

def writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat = ""):
    if InnValuta == "USDC":
        Inn = Inn * float(10**12)
    elif UtValuta == "USDC":
        Ut = Ut * float(10**12)
    csvwriter.writerow([timestamp, \
                        Type, \
                        str(float(Inn)/float(10**18)), \
                        InnValuta, \
                        str(float(Ut)/float(10**18)), \
                        UtValuta, \
                        str(float(Gebyr)/float(10**18)), \
                        gebyrValuta, \
                        marked, \
                        Notat])

def writetx(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat = ""):
    global timestamp, csvwriter, csverrorwriter, transactionid, gebyrValuta, \
        marked, MexPrice, RidePrice
    # Tidspunkt,Type,Inn,Inn-Valuta,Ut,Ut-Valuta,Gebyr,Gebyr-Valuta,Marked,Notat
    try:    InnValuta = InnValuta.split("-")[0]
    except: pass
    try:    UtValuta = UtValuta.split("-")[0]
    except: pass
    if (InnValuta == "MEX" or InnValuta == "LKMEX" or InnValuta == "RIDE") and \
        Ut == 0 and Type == "Inntekt":
        epoch = timestamp.strftime("%d-%m-%Y")
        UtValuta = "NOK"
        try:
            if InnValuta in ["MEX", "LKMEX"]:
                 Ut = float(MexPrice[epoch]) * Inn
            elif InnValuta == "RIDE":
                 Ut = float(RidePrice[epoch]) * Inn
            else:
                 Ut = 1*float(10**18)
        except KeyError:
            Ut = 1*float(10**18)
    if Type == "Handel":
        #If both variables are not EGLD:
        if InnValuta != "EGLD" and UtValuta != "EGLD":
            # Now depends what's the unknown.
            # WEGLD == EGLD
            if InnValuta == "WEGLD" or UtValuta == "WEGLD":
                Notat = Notat + " Inserted extra step due to unknown value"
                if InnValuta == "WEGLD":
                    writerow(Type, Inn, "EGLD", Ut, UtValuta, Gebyr, Notat)
                    writerow(Type, Inn, InnValuta, Inn, "EGLD", 0, Notat)
                elif UtValuta == "WEGLD":
                    writerow(Type, Ut, "EGLD", Ut, UtValuta, Gebyr, Notat)
                    writerow(Type, Inn, InnValuta, Ut, "EGLD", 0, Notat)
            # else if , we should look at MEX or RIDE value
            elif InnValuta in ["MEX", "LKMEX", "RIDE"] or \
                 UtValuta  in ["MEX", "LKMEX", "RIDE"]:
                Notat = Notat + " Inserted extra step due to unknown value"
                epoch = timestamp.strftime("%d-%m-%Y")
                if InnValuta in ["MEX", "LKMEX"]:
                    Nok = float(MexPrice[epoch]) * Inn
                elif UtValuta in ["MEX", "LKMEX"]:
                    Nok = float(MexPrice[epoch]) * Ut
                elif InnValuta == "RIDE":
                    Nok = float(RidePrice[epoch]) * Inn
                else:
                    Nok = float(RidePrice[epoch]) * Ut
                if InnValuta in ["MEX", "LKMEX", "RIDE"]:
                    writerow(Type, Inn, InnValuta, Nok, "NOK", Gebyr, Notat)
                    writerow(Type, Nok, "NOK", Ut, UtValuta, 0, Notat)
                elif UtValuta in ["MEX", "LKMEX", "RIDE"]:
                    writerow(Type, Nok, "NOK", Ut, UtValuta, Gebyr, Notat)
                    writerow(Type, Inn, InnValuta, Nok, "NOK", 0, Notat)
            else:
                writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat) 
        else:
            writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat)      
    else:
        writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat)

def csvparser():
    global egld, stakedegld, ESDTs, timestamp, \
        csvwriter, csverrorwriter, transactionid, gebyrValuta, marked, \
            MexPrice, RidePrice
    url = "https://api.elrond.com/accounts/" + wallet_address + \
        "/transactions?size=1000&before=1640991600&after=1609455600&withLogs=false"
    print(url)
    transactions = requests.get(url).json()
    with open('Elrond_Transactions.csv', 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow(["Tidspunkt","Type","Inn","Inn-Valuta","Ut",
                           "Ut-Valuta","Gebyr","Gebyr-Valuta","Marked","Notat"])
        with open("mexprices.json", "r") as mexprices:
            MexPrice = json.load(mexprices)
        with open("rideprices.json", "r") as rideprices:
            RidePrice = json.load(rideprices)
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
                        while fulltx.status_code == 429:
                            time.sleep(1)
                            print("sleeping...")
                            fulltx = requests.get("https://api.elrond.com/transactions/"+transactionid)
                        fulltxjson = fulltx.json()
                        Tokenssent = {}
                        Tokensreceived = {}
                        # Check what we've received.
                        for operation in fulltxjson["operations"]:
                            if operation["action"] == "transfer":
                                try:
                                    ticker = operation["identifier"].split("-")[0]
                                except KeyError:
                                    ticker = "EGLD"
                                ESDTvalue = int(operation["value"])
                                total = 0
                                if ticker in ESDTs.keys():
                                    total = ESDTs.get(ticker)
                                if operation["receiver"] == wallet_address and \
                                   ticker != "EGLD":
                                    total += ESDTvalue
                                    if ticker not in Tokensreceived:
                                        Tokensreceived[ticker] = ESDTvalue
                                    else:
                                        print("Found duplicate! " + ticker)
                                        Tokensreceived[ticker + "-1"] = ESDTvalue
                                elif operation["receiver"] == wallet_address:
                                    egld += ESDTvalue
                                    Tokensreceived[ticker] = ESDTvalue
                                if operation["sender"] == wallet_address:
                                    total -= ESDTvalue
                                    Tokenssent[ticker] = ESDTvalue
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
                                        name)
                            del Tokensreceived[mainticker]
                            for key in Tokensreceived.keys():
                                writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
                        elif name == "removeLiquidity":
                            print(transactionid)
                            mainticker = list(Tokenssent.keys())[0]
                            firsttoken = list(Tokensreceived.keys())[0]
                            secondtoken = list(Tokensreceived.keys())[1]
                            writetx("Handel", Tokensreceived[firsttoken], firsttoken,
                                        Tokenssent[mainticker] / 2,
                                        mainticker, fee / 2,
                                        name)
                            writetx("Handel", Tokensreceived[secondtoken], secondtoken,
                                        Tokenssent[mainticker] / 2,
                                        mainticker, fee / 2,
                                        name)
                            del Tokensreceived[firsttoken]
                            del Tokensreceived[secondtoken]
                            for key in Tokensreceived.keys():
                                writetx("Inntekt", Tokensreceived[key], key, 0, "", 0, name)
                            del Tokenssent[mainticker]
                            for key in Tokenssent.keys():
                                writetx("Overføring-Ut", Tokenssent[key], key, 0, "", 0, name)
                        elif name == "enterFarm" or name == "compoundRewards":
                            for key in Tokenssent.keys():
                                if key in Tokensreceived.keys():
                                    difference = Tokensreceived[key] - Tokenssent[key]
                                    del Tokensreceived[key]
                                    if difference > 0:
                                        writetx("Erverv", difference, key, 0, "", 0, name)
                                else:
                                    # Since we're entering a farm, the tokens aren't really lost. So Overføring-Ut.
                                    writetx("Overføring-Ut", 0, "", Tokenssent[key], key, 0, name)
                            for key in Tokensreceived.keys():
                                # Any tokens we receive we treat as Erverv, as we're not going to attach
                                # any value to them.
                                writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
                            writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                        elif name == "exitFarm":
                            for key in Tokenssent.keys():
                                if key in Tokensreceived.keys():
                                    difference = Tokenssent[key] - Tokensreceived[key]
                                    del Tokensreceived[key]
                                    if difference > 0:
                                        writetx("Tap-uten-fradrag", 0, "", difference, key, 0, name)
                                else:
                                    writetx("Tap-uten-fradrag", 0, "", Tokenssent[key], key, 0, name)
                            # The first transfer is our own tokens. Treat as Overføring-Inn
                            writetx("Overføring-Inn", list(Tokensreceived.values())[0], \
                                    list(Tokensreceived.keys())[0], 0, "", 0, name)
                            # The second transfer (if any) is rewards. Treat as Inntekt
                            try:
                                writetx("Inntekt", list(Tokensreceived.values())[1], \
                                        list(Tokensreceived.keys())[1], 0, "", 0, name)
                            except IndexError:
                                pass
                            writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                        elif name == "mergeLockedAssetTokens":
                            writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, name + " fee")
                        elif name == "swap":
                            swapout = transaction["action"]["arguments"]["transfers"][0]["token"]
                            swapin = transaction["action"]["arguments"]["transfers"][1]["token"]
                            swapout = swapout.split("-")[0]
                            swapin = swapin.split("-")[0]
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
                                if key in Tokensreceived.keys():
                                    difference = Tokenssent[key] - Tokensreceived[key]
                                    del Tokensreceived[key]
                                    if difference > 0:
                                        writetx("Tap-uten-fradrag", 0, "", difference, key, 0, name)
                            for key in Tokensreceived.keys():
                                if key == "MEX" or \
                                    key == "LKMEX" or \
                                     key == "EGLD" or \
                                      key == "RIDE":
                                      writetx("Inntekt", Tokensreceived[key], key, 0, "", 0, name)
                                else:
                                    writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
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
                    if "arguments" in transaction["action"]:
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
            if egld < -0.001*(10**18):
                print(transactionid)
                break
            try:
                pass
                #print(timestamp.isoformat() + " LKMEX: " + \
                #      str(ESDTs["LKMEX"]/float(10**18)) + " " + \
                #          transactionid + " " + name)
                #print("EGLD :" + str(float(egld)/float(10**18)) + \
                #      ". Staked: " + str(float(stakedegld)/float(10**18)) + \
                #          ". Hash:" + transactionid + name)
            except:
                pass
        print("EGLD :" + str(float(egld)/float(10**18)) + \
              ". Staked: " + str(float(stakedegld)/float(10**18)) + \
                  ". Hash:" + transactionid)
        for ESDT in ESDTs:    
            print(ESDT + ": " + str(float(ESDTs[ESDT])/float(10**18)))

if __name__ == "__main__":
    csvparser()
