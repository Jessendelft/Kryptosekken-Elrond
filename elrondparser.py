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
import warnings
warnings.filterwarnings("ignore")

wallet_address = ""

true_LKMEX_values = False

#For testing purposes, we can keep track of our ESDT's in the script.
ESDTs = {}
timestamp = 0
csvwriter = 0
csverrorwriter = 0
transactionid = 0
gebyrValuta = "EGLD"
marked = "Elrond"
PriceData = {}
Tokendecimals = {"EGLD":18, "LKMEX":18, "NOK":18}

def getURL(url):
    fulltx = requests.get(url, verify=False)
    while fulltx.status_code == 429:
        time.sleep(1)
        print("sleeping...")
        fulltx = requests.get(url, verify=False)
    return fulltx

def writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat = ""):
    global Tokens
    try:    InnValutaSplit = InnValuta.split("-")[0]
    except: InnValutaSplit = InnValuta
    try:    UtValutaSplit = UtValuta.split("-")[0]
    except: UtValutaSplit = UtValuta
    # Get the decimal count of new tokens
    if InnValutaSplit not in Tokendecimals and \
       InnValutaSplit != "":
        try:
            url = "https://api.elrond.com/tokens/" + InnValuta
            tokenomics = getURL(url).json()
            Tokendecimals[InnValutaSplit] = tokenomics["decimals"]
        except KeyError:
            pass
    if UtValutaSplit not in Tokendecimals and \
       UtValutaSplit != "":
        try:
            url = "https://api.elrond.com/tokens/" + UtValuta
            tokenomics = getURL(url).json()
            Tokendecimals[UtValutaSplit] = tokenomics["decimals"]
        except KeyError:
            pass
    # Correct the decimal count
    if InnValutaSplit != "":
        if InnValutaSplit in Tokendecimals:
            Inn = Inn / float(10**Tokendecimals[InnValutaSplit])
    if UtValutaSplit != "":
        if UtValutaSplit in Tokendecimals:
            Ut = Ut / float(10**Tokendecimals[UtValutaSplit])
    csvwriter.writerow([timestamp, \
                        Type, \
                        str(Inn), \
                        InnValutaSplit, \
                        str(Ut), \
                        UtValutaSplit, \
                        str(float(Gebyr)/float(10**18)), \
                        gebyrValuta, \
                        marked, \
                        Notat + " " + transactionid])

def getPriceData(token, epoch):

    global PriceData
    # If we don't have USD data, get that first from Norges Bank.
    if "USD" not in PriceData:
        print("Getting USD")
        datelist = []
        startdate = epoch
        enddate = str(datetime.date.today())
        url = "https://data.norges-bank.no/api/data/EXR/B.USD.NOK.SP?format=sdmx-json&startPeriod=" + \
            startdate + "&endPeriod=" + enddate + "&locale=no"
        usdcourse = getURL(url).json()
        # Check if the first date recovered is actually in the data. Important for later.
        while startdate not in usdcourse["data"]["structure"]["dimensions"]["observation"][0]["values"][0]["id"]:
            startdatetm = datetime.datetime.strptime(startdate, "%Y-%m-%d")
            startdate = datetime.datetime.strftime(startdatetm - datetime.timedelta(days=1), "%Y-%m-%d")
            url = "https://data.norges-bank.no/api/data/EXR/B.USD.NOK.SP?format=sdmx-json&startPeriod=" + \
                startdate + "&endPeriod=" + enddate + "&locale=no"
            usdcourse = getURL(url).json()
        # Recover date & value info from our query.
        for observation in usdcourse["data"]["dataSets"][0]["series"]["0:0:0:0"]["observations"]:
            price = float(usdcourse["data"]["dataSets"][0]["series"]["0:0:0:0"]["observations"][observation][0])
            date = usdcourse["data"]["structure"]["dimensions"]["observation"][0]["values"][int(observation)]["id"]
            datelist.append(datetime.datetime.strptime(date, "%Y-%m-%d"))
            if "USD" in PriceData:
                PriceData["USD"][date] = price
            else:
                PriceData["USD"] = {}
                PriceData["USD"][date] = price
        # Now we fill in the blanks
        for date in datelist:
            checking = date + datetime.timedelta(days=1)
            while checking not in datelist and \
                checking < datetime.datetime.strptime(enddate, "%Y-%m-%d"):
                addeddate = datetime.datetime.strftime(checking, "%Y-%m-%d")
                addedvalue = PriceData["USD"][datetime.datetime.strftime( \
                                checking - datetime.timedelta(days=1), "%Y-%m-%d")]
                PriceData["USD"][addeddate] = addedvalue
                checking = checking + datetime.timedelta(days=1)
    # Temporary fix; chance EGLD to WEGLD.
    if token == "EGLD":
        token = "WEGLD-bd4d79"
    # Then we get the rest.
    if token not in PriceData:
        url = "https://graph.maiar.exchange/graphql"
        query = """{
                values24h(metric: "priceUSD", series: \"""" + token + """\") {
                    timestamp
                    value
                  }
                }"""
        r = requests.post(url, json={'query': query}, verify=False)
        result = json.loads(r.text)
        for pricepoint in result["data"]["values24h"]:
            timestamp = pricepoint["timestamp"].split(" ")[0]
            price = float(pricepoint["value"])
            if token in PriceData:
                PriceData[token][timestamp] = price
            else:
                PriceData[token] = {}
                PriceData[token][timestamp] = price
    # Now it's time to return the price. If it's not available, we look forward in time.
    date = datetime.datetime.strptime(epoch, "%Y-%m-%d")
    while datetime.datetime.strftime(date, "%Y-%m-%d") not in PriceData[token]:
        date = date + datetime.timedelta(days=1)
    price = PriceData[token][datetime.datetime.strftime(date, "%Y-%m-%d")]
    # Convert to NOK:
    price = price * PriceData["USD"][epoch]
    return price

def writetx(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat = ""):
    """ 
    This entire function needs to be re-written:
        1. Check if LKMEX. If so, check if we're writing 1/1.000.000th NOK/LKMEX or MEX-455c57 value
        2. Check if it's Inntekt or Handel
           a. If so, check if we have price data. If not, retrieve from https://graph.maiar.exchange/graphql. Save in nested Dict
              {Token: {epoch:price}}
           b. Retrieve USD/NOK price data from NorskeBanken, and change USD to NOK
           c. Write out handel.
        
    """
    global timestamp, csvwriter, csverrorwriter, transactionid, gebyrValuta, \
        marked
    try:    InnValutaSplit = InnValuta.split("-")[0]
    except: pass
    try:    UtValutaSplit = UtValuta.split("-")[0]
    except: pass
    epoch = timestamp.strftime("%Y-%m-%d")
    # Check if we're receiving something that we need to valuate
    if Ut == 0 and Type == "Inntekt":
        UtValuta = "NOK"
        # Check if LKMEX. If so, check if we're following MEX price or 'fake' price.
        if InnValutaSplit == "LKMEX":
            if true_LKMEX_values:
                Ut = getPriceData("MEX-455c57", epoch) * Inn
            else:
                Ut = Inn / float(10**6)
        else:
            Ut = getPriceData(InnValuta, epoch) * Inn
    if Type == "Handel":
        # We need to determine if InnValuta or UtValuta is known.
        Notat = Notat + " Inserted extra step due to unknown value"
        try:
            # Check if LKMEX. If so, check if we're following MEX price or 'fake' price.
            if InnValutaSplit == "LKMEX":
                if true_LKMEX_values:
                    Nok = getPriceData("MEX-455c57", epoch) * Inn
                else:
                    Nok = Inn / float(10**6)
            else:
                Nok = getPriceData(InnValuta, epoch) * Inn
            writerow(Type, Nok, "NOK", Ut, UtValuta, Gebyr, Notat)
            writerow(Type, Inn, InnValuta, Nok, "NOK", 0, Notat)
        except:
            # Check if LKMEX. If so, check if we're following MEX price or 'fake' price.
            try:
                if UtValutaSplit == "LKMEX":
                    if true_LKMEX_values:
                        Nok = getPriceData("MEX-455c57", epoch) * Ut
                    else:
                        Nok = Ut / float(10**6)
                else:
                    Nok = getPriceData(UtValuta, epoch) * Ut
                writerow(Type, Inn, InnValuta, Nok, "NOK", 0, Notat)
                writerow(Type, Nok, "NOK", Ut, UtValuta, Gebyr, Notat)
            except:
                writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat)
    else:
        writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat)

def csvparser():
    global ESDTs, timestamp, \
        csvwriter, csverrorwriter, transactionid, gebyrValuta, marked
    url = "https://api.elrond.com/accounts/" + wallet_address + \
        "/transfers?size=1000&withLogs=false&after=1640991600"
    transactions = getURL(url).json()
    with open('Elrond_Transactions.csv', 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow(["Tidspunkt","Type","Inn","Inn-Valuta","Ut",
                           "Ut-Valuta","Gebyr","Gebyr-Valuta","Marked","Notat"])
        # Now the main loop starts
        for transaction in reversed(transactions):
            try:
                fee = int(transaction["fee"])
            except KeyError:
                fee = 0
            timestamp = datetime.datetime.fromtimestamp(transaction["timestamp"])
            transactionid = transaction["txHash"]
            # First, check if the transaction actually succeeded.
            if transaction["status"] != "success":
                writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "failed")
            elif transaction["sender"] == wallet_address:
                function = ""
                fulltx = []
                Tokenssent = {}
                Tokensreceived = {}
                # Try to read the function field.
                if "function" in transaction:
                    function = transaction["function"]
                if function in ["stakeFarm", "exitFarm"]:
                    name = transaction["action"]["name"]
                    # Get the full transaction details.
                    fulltx = getURL("https://api.elrond.com/transactions/"+transactionid).json()
                    Tokenssent, Tokensreceived = getTokens(fulltx)
                    {'stakeFarm': enterFarm, 
                     'exitFarm': exitFarm
                     }[function](name, fee, transaction, fulltx, Tokenssent, Tokensreceived)
                # Try to read the action field.
                elif "action" in transaction:
                    name = transaction["action"]["name"]
                    # Get the full transaction details. Not needed for everything, and slows things down.
                    if name not in ["delegate", "unDelegate", "stake", "wrapEgld", "unwrapEgld"]:
                        fulltx = getURL("https://api.elrond.com/transactions/"+transactionid).json()
                    # Make an overview of what has gone in & what has gone out.
                    if "operations" in fulltx:
                        Tokenssent, Tokensreceived = getTokens(fulltx)
                    # Secondly, we write to our csv file depending on the type.
                    try:
                        {'delegate': stake, 
                         'unDelegate': feeOnly, 
                         'stake': stake,
                         'wrapEgld': wrapEgld,
                         'unwrapEgld': unwrapEgld,
                         'confirmTickets': confirmTickets,
                         'unBond': unStake,
                         'withdraw': unStake,
                         "unStake": unStake,
                         "reDelegateRewards": reDelegateRewards,
                         "claimLockedAssets": claimLockedAssets,
                         "claimLaunchpadTokens": claimLaunchpadTokens,
                         "addLiquidity": addLiquidity,
                         "removeLiquidity": removeLiquidity,
                         "compoundRewards": compoundRewards,
                         "enterFarm": enterFarm,
                         "exitFarm": exitFarm,
                         "unlockAssets": exitFarm,
                         "mergeLockedAssetTokens": feeOnly,
                         "swap": swap,
                         "claimRewards": claimRewards,
                         "issueSemiFungable": feeOnly,
                         "buy": getNFT,
                         "buyNft": getNFT,
                         "mint": getNFT,
                         "enterSale": getNFT
                         }[name](name, fee, transaction, fulltx, Tokenssent, Tokensreceived)
                    except KeyError:
                        undefined_tx(name, fee, transaction, fulltx, Tokenssent, Tokensreceived)
                #if no "action", it's just a regular transfer out:
                else:
                    eGLDvalue = int(transaction["value"])
                    writetx("Overføring-Ut", 0, "", eGLDvalue, "EGLD", fee,\
                            "Regular transfer out. Double check this type!")
            # Check if we're receiving something, and if yes, what it is
            elif transaction["receiver"] == wallet_address:
                # Try to read the action field.
                if "action" in transaction:
                    name = transaction["action"]["name"]
                    if "arguments" in transaction["action"] and "originalTxHash" not in transaction:
                        for transfer in transaction["action"]["arguments"]["transfers"]:
                            total = 0
                            ESDTvalue = int(transfer["value"])
                            try:
                                ticker = transfer["token"]
                            except KeyError:
                                ticker = transfer["ticker"]
                            if ticker in ESDTs.keys():
                                total = ESDTs.get(ticker)
                            ESDTs[ticker] = total + ESDTvalue
                            writetx("Erverv", ESDTvalue, ticker, 0, "", 0, \
                                    name + ", Regular transfer in. Double check this type!")
                    else:
                        writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")
                else:
                    if transaction["type"] == "Transaction" and "action" not in transaction:
                        fulltx = getURL("https://api.elrond.com/transactions/"+transactionid).json()
                        if "receipt" in fulltx:
                            if fulltx["receipt"]["data"] == "refundedGas":
                                writetx("Erverv", fee, "EGLD", 0, "", 0,
                                        "refundedGas. Double check this type!")
                    else:
                        eGLDvalue = int(transaction["value"])
                        writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", fee,
                                "Regular transfer in. Double check this type!")
            else:
                print("unknown")
                print(transactionid)
        for ESDT in ESDTs:    
            print(ESDT + ": " + str(float(ESDTs[ESDT])/float(10**18)))

def getTokens(fulltx):
    Tokenssent = {}
    Tokensreceived = {}
    for operation in fulltx["operations"]:
        if operation["action"] == "transfer":
            try:
                ticker = operation["identifier"]
            except KeyError:
                ticker = "EGLD"
            if len(ticker.split("-")) > 2:
                ticker = ticker.split("-")[0] + "-" + ticker.split("-")[1]
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
                Tokensreceived[ticker] = ESDTvalue
            if operation["sender"] == wallet_address:
                total -= ESDTvalue
                Tokenssent[ticker] = ESDTvalue
            ESDTs[ticker] = total
    return Tokenssent, Tokensreceived

def feeOnly(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """write only fee costs"""
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, name)
    
def stake(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Staking (legacy)"""
    eGLDvalue = int(transaction["value"])
    writetx("Overføring-Ut", 0, "", eGLDvalue, "EGLD", fee, name)
    
def wrapEgld(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """wrapEGLD == handel"""
    eGLDvalue = int(transaction["action"]["arguments"]["token"]["value"])
    ticker = transaction["action"]["arguments"]["token"]["token"]
    total = 0
    if ticker in ESDTs.keys():
        total = ESDTs.get(ticker)
    ESDTs[ticker] = total + eGLDvalue
    writetx("Handel", eGLDvalue, ticker, eGLDvalue, "EGLD", fee, name)
    
def unwrapEgld(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """unwrapEgld == handel"""
    for transfer in transaction["action"]["arguments"]["transfers"]:
        eGLDvalue = int(transfer["value"])
        ticker = transfer["ticker"]
        total = 0
        if ticker in ESDTs.keys():
            total = ESDTs.get(ticker)
        ESDTs[ticker] = total - eGLDvalue
        writetx("Handel", eGLDvalue, "EGLD", eGLDvalue, ticker, 0, name)
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")

def confirmTickets(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """confirm our Tickets"""
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")

def unStake(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """unStaking (legacy)"""
    for result in fulltx["results"]:
        if fulltx["receiver"] == wallet_address:
            eGLDvalue = int(result["value"])
            writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", 0, name)
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")

def reDelegateRewards(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """reDelegating"""
    for result in fulltx["results"]:
        if result["receiver"] == wallet_address:
            eGLDvalue = int(result["value"])
            writetx("Inntekt", eGLDvalue, "EGLD", 0, "EGLD", 0, name)
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")

def claimLockedAssets(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """claim first LKMEX batch == inntekt"""
    for operation in fulltx["operations"]:
        if operation["action"] == "transfer":
            ticker = "LKMEX-aab910"
            total = 0
            ESDTvalue = int(operation["value"])
            if ticker in ESDTs.keys():
                total = ESDTs.get(ticker)
            ESDTs[ticker] = total + ESDTvalue
            writetx("Inntekt", ESDTvalue, ticker, 0, "EGLD", 0, name)
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")

### Needs re-write, as RIDE is not the only launchpad token any longer.
def claimLaunchpadTokens(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """claim Launchpad tokens. Claim == inntekt"""
    for operation in fulltx["operations"]:
        if operation["type"] == "egld":
            total = 0
            eGLDvalue = int(operation["value"])
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

def addLiquidity(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Add liquidity = Handel. Anything extra = Inntekt (LKMEX rewards)"""
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

def removeLiquidity(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Removing liquidity = Handel. Anything extra = Inntekt (LKMEX rewards)"""
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

def compoundRewards(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Compounding rewards = Erverv (we're not going to attach any value to them now)"""
    for key in Tokenssent.keys():
        if key in Tokensreceived.keys():
            difference = Tokensreceived[key] - Tokenssent[key]
            del Tokensreceived[key]
            if difference > 0:
                writetx("Erverv", difference, key, 0, "", 0, name)
        else:
            # Anything else we don't know or care. Overføring ut.
            writetx("Overføring-Ut", 0, "", Tokenssent[key], key, 0, name)
    for key in Tokensreceived.keys():
        writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")

def enterFarm(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Entering the farm = Handel. Anything extra = Erverv"""
    topreceived = list(Tokensreceived.keys())[0]
    for key in Tokensreceived.keys():
        # When we enter a farm it can be that we already staked to that farm.
        # In that case, Elrond will send us a sum of all tokens, including the new ones we put in.
        if key in Tokenssent.keys():
            difference = Tokensreceived[key] - Tokenssent[key]
            Tokensreceived[key] = difference
            del Tokenssent[key]
    for key in Tokenssent.keys():
        # For each token we sent, 
        writetx("Handel", Tokensreceived[topreceived]/len(Tokenssent.keys()), \
                topreceived, Tokenssent[key], key, 0, name)
    del Tokensreceived[topreceived]
    for key in Tokensreceived.keys():
        writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)

def exitFarm(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Exiting the farm = Handel on the farm tokens. Anything extra = Inntekt"""
    topreceived = list(Tokensreceived.keys())[0]
    deleted = False
    for key in Tokenssent.keys():
        if key in Tokensreceived.keys():
            difference = Tokenssent[key] - Tokensreceived[key]
            Tokenssent[key] = difference
    if len(Tokenssent.keys()) > 0:
        for key in Tokenssent.keys():
            #If our main income is MEX, LKMEX or RIDE, we should treat it as a Handel
            writetx("Handel", Tokensreceived[topreceived]/len(Tokenssent.keys()), \
                    topreceived, Tokenssent[key], key, 0, name)
        del Tokensreceived[topreceived]
        deleted = True
    try:
        if deleted:
            # The transfer (if any) are rewards. Treat as Inntekt
            writetx("Inntekt", list(Tokensreceived.values())[0], \
                    list(Tokensreceived.keys())[0], 0, "", 0, name)
        else:
            # The first transfer is our own tokens. Treat as Overføring-Inn
            writetx("Overføring-Inn", list(Tokensreceived.values())[0], \
                    list(Tokensreceived.keys())[0], 0, "", 0, name)
            # The second transfer (if any) is rewards. Treat as Inntekt
            writetx("Inntekt", list(Tokensreceived.values())[1], \
                    list(Tokensreceived.keys())[1], 0, "", 0, name)
    except IndexError:
        pass

def swap(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Swapping = Handel"""
    swapout = transaction["action"]["arguments"]["transfers"][0]["token"]
    swapin = transaction["action"]["arguments"]["transfers"][1]["token"]
    #swapout = swapout.split("-")[0]
    #swapin = swapin.split("-")[0]
    writetx("Handel", Tokensreceived[swapin], swapin, \
            Tokenssent[swapout], swapout, fee, name)
    del Tokensreceived[swapin]
    del Tokenssent[swapout]
    for key in Tokenssent.keys():
        writetx("Inntekt", Tokenssent[key], key, 0, "", 0, name)
    for key in Tokensreceived.keys():
        writetx("Inntekt", Tokensreceived[key], key, 0, "", 0, name)

def claimRewards(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Claiming rewards. If EGLD, Inntekt. Otherwise Erverv"""
    for key in Tokenssent.keys():
        if key in Tokensreceived.keys():
            difference = Tokenssent[key] - Tokensreceived[key]
            del Tokensreceived[key]
            if difference > 0:
                writetx("Tap-uten-fradrag", 0, "", difference, key, 0, name)
    for key in Tokensreceived.keys():
        if key == "EGLD":
              writetx("Inntekt", Tokensreceived[key], key, 0, "", 0, name)
        else:
            writetx("Erverv", Tokensreceived[key], key, 0, "", 0, name)
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "fee")

def getNFT(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Getting NFT's. Through Handel."""
    EGLDvalue = float(fulltx["value"])
    for key in Tokensreceived.keys():
        writetx("Handel",  Tokensreceived[key], key, EGLDvalue/len(Tokensreceived.keys()), "EGLD", fee, name)

def undefined_tx(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Anything undefined"""
    print("Not Defined: " + name + ". Hash: " + transactionid)
    for key in Tokensreceived.keys():
        writetx("Overføring-Inn", Tokensreceived[key], key, 0, "", 0, "Not Recognized: " + name)
    for key in Tokenssent.keys():
        writetx("Overføring-Ut", 0, "", Tokenssent[key], key, 0, "Not Recognized: " + name)
    writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, name + " fee")

            
            
if __name__ == "__main__":
    #getPriceData("MEX-455c57", "2021-11-24")
    csvparser()
