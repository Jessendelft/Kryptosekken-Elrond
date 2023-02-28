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

"""User configurable"""
wallet_address = ""         ### Wallet address of the user
true_LKMEX_values = False   ### Uses the true market value of LKMEX.
txidinnotat = False         ### Adds the transaction ID in the notat field.
ownWalletlist = []          ### Optional ownWalletlist used to destinguish transfers between own wallets.
aliases = { "erd1w9mmxz6533m7cf08gehs8phkun2x4e8689ecfk3makk3dgzsgurszhsxk4":"eMoon Marketplace",
            "erd1qqqqqqqqqqqqqpgqd9rvv2n378e27jcts8vfwynpx0gfl5ufz6hqhfy0u0":"Deadrare Marketplace",
            "erd1qqqqqqqqqqqqqpgq6wegs2xkypfpync8mn2sa5cmpqjlvrhwz5nqgepyg8":"XOXNO Marketplace",
            "erd1deaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaddeaqtv0gag":"Burn Wallet",
            "erd12v2r3q33g43hju8smz6g4sgsqsxaut3e5lnjr5r3xrljqj3pwfmq0pxhz6":"Aerovek"} # Optional Aliases used to replace wallet values in notat field.
startdate = datetime.datetime(2022,1,1)     ### Start date
enddate = datetime.datetime(2023,1,1)       ### End date
marked = "Elrond"           ### Market text.

"""Global variables"""
APIaddress = "https://api.multiversx.com"
timestamp = 0
csvwriter = 0
csverrorwriter = 0
transactionid = 0
gebyrValuta = "EGLD"
PriceData = {}
Tokendecimals = {"EGLD":18, "LKMEX":18, "NOK":18}
registeredfees = []
nexturlrequest = datetime.datetime.now() + datetime.timedelta(seconds = 1)
urlrequestsleft = 2

def delayURL():
    """Delays URL queries based upon max 2/ip/second rule"""
    global urlrequestsleft, nexturlrequest
    now = datetime.datetime.now()
    if now < nexturlrequest:
        print("Queries left this second: " + str(urlrequestsleft))
        urlrequestsleft -= 1
        if not urlrequestsleft:
            print("Sleeping : " + str((nexturlrequest - now).total_seconds()) + " seconds")
            time.sleep((nexturlrequest - now).total_seconds())
            time.sleep(0.1)
    else:
        urlrequestsleft = 2
        nexturlrequest = now + datetime.timedelta(seconds = 1)

def getURL(url):
    """Provide a URL, get the result"""
    delayURL()
    fulltx = requests.get(url, verify=False)
    while fulltx.status_code not in [200, 400, 404]:
        print("Error retrieving from server, status code: " + str(fulltx.status_code))
        delayURL()
        fulltx = requests.get(url, verify=False)
    return fulltx

def postURL(url, json):
    """Provide a URL with a json argument, get the result"""
    delayURL()
    fulltx = requests.post(url, json=json, verify=False)
    while fulltx.status_code not in [200, 400, 404]:
        print("Error retrieving from server, status code: " + str(fulltx.status_code))
        delayURL()
        fulltx = requests.get(url, json=json, verify=False)
    return fulltx

def AliasSwap(check_for_alias_tx, field = "dummy"):
    """
    Swaps out addresses for aliases. Prioritizes the aliases variable.
    Queries the multiversx api if no alias is known.
    """
    global aliases
    check_tx = {}
    if type(check_for_alias_tx) == str: check_tx[field] = check_for_alias_tx
    else: check_tx[field] = check_for_alias_tx[field]
    ### First we check our manual database
    if check_tx[field] in aliases: check_tx[field] = aliases[check_tx[field]]
    ### Next we check if we already received an Assets field
    elif (field+"Assets") in check_tx:
        check_tx[field] = check_tx[field+"Assets"]
    ### If not, we start spamming the server
    else:
        SmartContract = False
        accountdetails = getURL(APIaddress + "/accounts/" + check_tx[field]).json()
        if "erd1qqqqqqqqqqqqqp" in check_tx[field]:
            #"erd1qqqqqqqqqqqqqp" == Smart Contract. Find the owner.
            if "assets" in accountdetails:
                aliases[check_tx[field]] = accountdetails["assets"]["name"]
                check_tx[field] = accountdetails["assets"]["name"]
            else:
                check_tx[field] = accountdetails["ownerAddress"]
                accountdetails = getURL(APIaddress + "/accounts/" + accountdetails["ownerAddress"]).json()
                SmartContract = True
        if "username" in accountdetails:
            aliases[check_tx[field]] = accountdetails["username"]
            check_tx[field] = accountdetails["username"]
        if SmartContract:
            aliases[field] = "Smart Contract owned by " + check_tx[field]
            check_tx[field] = "Smart Contract owned by " + check_tx[field]
    return check_tx[field]

def writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat = ""):
    global Tokens, registeredfees
    try:    InnValutaSplit = InnValuta.split("-")[0]
    except: InnValutaSplit = InnValuta
    try:    UtValutaSplit = UtValuta.split("-")[0]
    except: UtValutaSplit = UtValuta
    ### Get the decimal count of new tokens
    if InnValutaSplit not in Tokendecimals and \
       InnValutaSplit != "":
        try:
            url = APIaddress + "/tokens/" + InnValuta
            tokenomics = getURL(url).json()
            Tokendecimals[InnValutaSplit] = tokenomics["decimals"]
        except KeyError:
            pass
    if UtValutaSplit not in Tokendecimals and \
       UtValutaSplit != "":
        try:
            url = APIaddress + "/tokens/" + UtValuta
            tokenomics = getURL(url).json()
            Tokendecimals[UtValutaSplit] = tokenomics["decimals"]
        except KeyError:
            pass
    ### Correct the decimal count
    if InnValutaSplit != "":
        if InnValutaSplit in Tokendecimals:
            Inn = Inn / float(10**Tokendecimals[InnValutaSplit])
    if UtValutaSplit != "":
        if UtValutaSplit in Tokendecimals:
            Ut = Ut / float(10**Tokendecimals[UtValutaSplit])
    ### Check if we need to write the fee. Append tx id to list if we write a fee.
    if transactionid in registeredfees:
        Gebyr = 0
    else:
        registeredfees.append(transactionid)
    if txidinnotat: Notat = Notat + ". Tx ID: " + transactionid
    csvwriter.writerow([timestamp, \
                        Type, \
                        str(Inn), \
                        InnValutaSplit, \
                        str(Ut), \
                        UtValutaSplit, \
                        str(float(Gebyr)/float(10**18)), \
                        gebyrValuta, \
                        marked, \
                        Notat])

def getPriceData(token, epoch):
    global PriceData
    ### If we don't have USD data, get that first from Norges Bank.
    if "USD" not in PriceData:
        print("Getting USD")
        datelist = []
        startdate = epoch
        enddate = str(datetime.date.today())
        url = "https://data.norges-bank.no/api/data/EXR/B.USD.NOK.SP?format=sdmx-json&startPeriod=" + \
            startdate + "&endPeriod=" + enddate + "&locale=no"
        usdcourse = getURL(url).json()
        ### Check if the first date recovered is actually in the data. Important for later.
        while startdate not in usdcourse["data"]["structure"]["dimensions"]["observation"][0]["values"][0]["id"]:
            startdatetm = datetime.datetime.strptime(startdate, "%Y-%m-%d")
            startdate = datetime.datetime.strftime(startdatetm - datetime.timedelta(days=1), "%Y-%m-%d")
            url = "https://data.norges-bank.no/api/data/EXR/B.USD.NOK.SP?format=sdmx-json&startPeriod=" + \
                startdate + "&endPeriod=" + enddate + "&locale=no"
            usdcourse = getURL(url).json()
        ### Recover date & value info from our query.
        for observation in usdcourse["data"]["dataSets"][0]["series"]["0:0:0:0"]["observations"]:
            price = float(usdcourse["data"]["dataSets"][0]["series"]["0:0:0:0"]["observations"][observation][0])
            date = usdcourse["data"]["structure"]["dimensions"]["observation"][0]["values"][int(observation)]["id"]
            datelist.append(datetime.datetime.strptime(date, "%Y-%m-%d"))
            if "USD" in PriceData:
                PriceData["USD"][date] = price
            else:
                PriceData["USD"] = {}
                PriceData["USD"][date] = price
        ### Now we fill in the blanks
        for date in datelist:
            checking = date + datetime.timedelta(days=1)
            while checking not in datelist and \
                checking < datetime.datetime.strptime(enddate, "%Y-%m-%d"):
                addeddate = datetime.datetime.strftime(checking, "%Y-%m-%d")
                addedvalue = PriceData["USD"][datetime.datetime.strftime( \
                                checking - datetime.timedelta(days=1), "%Y-%m-%d")]
                PriceData["USD"][addeddate] = addedvalue
                checking = checking + datetime.timedelta(days=1)
    ### Temporary fix; chance EGLD to WEGLD.
    if token == "EGLD":
        token = "WEGLD-bd4d79"
    ### Then we get the rest.
    if token not in PriceData:
        url = "https://graph.xexchange.com/graphql"
        query = """{
                values24h(metric: "priceUSD", series: \"""" + token + """\") {
                    timestamp
                    value
                  }
                }"""
        r = postURL(url, json={'query': query})
        result = json.loads(r.text)
        for pricepoint in result["data"]["values24h"]:
            timestamp = pricepoint["timestamp"].split(" ")[0]
            price = float(pricepoint["value"])
            if token in PriceData:
                PriceData[token][timestamp] = price
            else:
                PriceData[token] = {}
                PriceData[token][timestamp] = price
    ### Now it's time to return the price. If it's not available, we look forward in time.
    date = datetime.datetime.strptime(epoch, "%Y-%m-%d")
    while datetime.datetime.strftime(date, "%Y-%m-%d") not in PriceData[token]:
        date = date + datetime.timedelta(days=1)
    price = PriceData[token][datetime.datetime.strftime(date, "%Y-%m-%d")]
    ### Convert to NOK:
    price = price * PriceData["USD"][epoch]
    return price

def writetx(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat = ""):
    """ 
    This entire function needs to be re-written:
        1. Check if LKMEX. If so, check if we're writing 1/1.000.000th NOK/LKMEX or MEX-455c57 value
        2. Check if it's Inntekt or Handel
           a. If so, check if we have price data. If not, retrieve from https://graph.xexchange.com/graphql. Save in nested Dict
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
    ### Check if we're receiving something that we need to valuate
    if Ut == 0 and Type == "Inntekt":
        UtValuta = "NOK"
        ### Check if LKMEX or XMEX. If so, check if we're following MEX price or 'fake' price.
        if InnValutaSplit in ["LKMEX", "XMEX"]:
            if true_LKMEX_values:
                Ut = getPriceData("MEX-455c57", epoch) * Inn
            else:
                Ut = Inn / float(10**6)
        else:
            Ut = getPriceData(InnValuta, epoch) * Inn
    if Type == "Handel" and \
        UtValutaSplit not in ["EGLD", "USDC"] and \
         InnValutaSplit not in ["USDC", "EGLD"]:
        ### We need to determine if InnValuta or UtValuta is known.
        Notat = Notat + " Inserted extra step due to unknown value"
        try:
            ### Check if LKMEX or XMEX. If so, check if we're following MEX price or 'fake' price.
            if InnValutaSplit in ["LKMEX", "XMEX"]:
                if true_LKMEX_values:
                    Nok = getPriceData("MEX-455c57", epoch) * Inn
                else:
                    Nok = Inn / float(10**6)
            else:
                Nok = getPriceData(InnValuta, epoch) * Inn
            writerow(Type, Nok, "NOK", Ut, UtValuta, Gebyr, Notat)
            writerow(Type, Inn, InnValuta, Nok, "NOK", Gebyr, Notat)
        except:
            ### Check if LKMEX or XMEX. If so, check if we're following MEX price or 'fake' price.
            try:
                if UtValutaSplit in ["LKMEX", "XMEX"]:
                    if true_LKMEX_values:
                        Nok = getPriceData("MEX-455c57", epoch) * Ut
                    else:
                        Nok = Ut / float(10**6)
                else:
                    Nok = getPriceData(UtValuta, epoch) * Ut
                writerow(Type, Inn, InnValuta, Nok, "NOK", Gebyr, Notat)
                writerow(Type, Nok, "NOK", Ut, UtValuta, Gebyr, Notat)
            except:
                writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat)
    else:
        writerow(Type, Inn, InnValuta, Ut, UtValuta, Gebyr, Notat)

def csvparser():
    global timestamp, wallet_address, \
        csvwriter, csverrorwriter, transactionid
    url = APIaddress + "/accounts/" + wallet_address + \
        "/transfers?size=1000&withLogs=false&after=" + str(int(startdate.timestamp())) + \
            "&before=" + str(int(enddate.timestamp()))
    transactions = getURL(url).json()
    wallet_address = AliasSwap(wallet_address)
    for address in range(len(ownWalletlist)):
        ownWalletlist[address] = AliasSwap(ownWalletlist[address])
    with open('Elrond_Transactions.csv', 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        csvwriter.writerow(["Tidspunkt","Type","Inn","Inn-Valuta","Ut",
                           "Ut-Valuta","Gebyr","Gebyr-Valuta","Marked","Notat"])
        ### Now the main loop starts
        for transaction in reversed(transactions):
            try:
                fee = int(transaction["fee"])
            except KeyError:
                fee = 0
            timestamp = datetime.datetime.fromtimestamp(transaction["timestamp"])
            transactionid = transaction["txHash"]
            function = ""
            fulltx = []
            Tokenssent = {}
            Tokensreceived = {}
            transaction["receiver"] = AliasSwap(transaction, "receiver")
            transaction["sender"] = AliasSwap(transaction, "sender")
            ### First, check if the transaction actually succeeded.
            if transaction["status"] != "success":
                writetx("Overføring-Ut", 0, "", 0, "EGLD", fee, "failed")
            elif transaction["sender"] == wallet_address:
                ### Try to read the function field.
                if "function" in transaction:
                    function = transaction["function"]
                if function in ["stakeFarm", "exitFarm", "migrateToNewFarm"]:
                    name = transaction["action"]["name"]
                    ### Get the full transaction details.
                    fulltx = getURL(APIaddress + "/transactions/" + transactionid).json()
                    Tokenssent, Tokensreceived = getTokens(fulltx)
                    {'stakeFarm': enterFarm, 
                     'exitFarm': exitFarm,
                     'migrateToNewFarm': swap
                     }[function](name, fee, transaction, fulltx, Tokenssent, Tokensreceived)
                ### Try to read the action field.
                elif "action" in transaction:
                    name = transaction["action"]["name"]
                    ### Get the full transaction details. Not needed for everything, and slows things down.
                    if name not in ["delegate", "unDelegate", "stake", "wrapEgld", "unwrapEgld"]:
                        fulltx = getURL(APIaddress + "/transactions/" + transactionid).json()
                    ### Make an overview of what has gone in & what has gone out.
                    Tokenssent, Tokensreceived = getTokens(fulltx)
                    ### Secondly, we write to our csv file depending on the type.
                    try:
                        # {'delegate': stake, 
                        #   'unDelegate': feeOnly, 
                        #   'stake': stake,
                        #   'wrapEgld': wrapEgld,
                        #   'unwrapEgld': unwrapEgld,
                        #   'confirmTickets': feeOnly,
                        #   'unBond': unStake,
                        #   'withdraw': unStake,
                        #   "unStake": unStake,
                        #   "reDelegateRewards": reDelegateRewards,
                        #   "claimLockedAssets": claimLockedAssets,
                        #   "claimLaunchpadTokens": claimLaunchpadTokens,
                        #   "addLiquidity": addLiquidity,
                        #   "removeLiquidity": removeLiquidity,
                        #   "compoundRewards": compoundRewards,
                        #   "enterFarm": enterFarm,
                        #   "exitFarm": exitFarm,
                        #   "unlockAssets": exitFarm,
                        #   "mergeLockedAssetTokens": feeOnly,
                        #   "swap": swap,
                        #   "claimRewards": claimRewards,
                        #   "issueSemiFungable": feeOnly,
                        #   "buy": getNFT,
                        #   "buyNft": getNFT,
                        #   "mint": getNFT,
                        #   "enterSale": getNFT,
                        #   "transfer": Transfer,
                        #   "ESDTNFTCreate": getNFT
                        #   }[name](name, fee, transaction, fulltx, Tokenssent, Tokensreceived)
                       { "buy": getNFT,
                         "buyNft": getNFT,
                         "mint": getNFT,
                         "enterSale": getNFT,
                         "transfer": Transfer,
                         "ESDTNFTCreate": getNFT
                         }[name](name, fee, transaction, fulltx, Tokenssent, Tokensreceived)
                    except KeyError:
                        # undefined_tx(name, fee, transaction, fulltx, Tokenssent, Tokensreceived)
                        pass
                ### if no "action", it's just a regular transfer out:
                else:
                    eGLDvalue = int(transaction["value"])
                    if transaction["receiver"] not in ownWalletlist:
                        writetx("Overføring-Ut", 0, "", eGLDvalue, "EGLD", fee,\
                                "Regular transfer out. Receiver: " + transaction["receiver"])
                    else:
                        writetx("Overføring-Ut", 0, "", eGLDvalue, "EGLD", fee,\
                                "transfer between own wallets")
            ### Check if we're receiving something, and if yes, what it is
            elif transaction["receiver"] == wallet_address:
                ### Try to read the action field.
                if "action" in transaction:
                    name = transaction["action"]["name"]
                    try:
                        {
                         "buy": getNFT,
                         "buyNft": getNFT,
                         "mint": getNFT,
                         "enterSale": getNFT
                         }[name](name, 0, transaction, fulltx, Tokenssent, Tokensreceived)
                    except:
                        if "arguments" in transaction["action"] and "originalTxHash" not in transaction:
                            for transfer in transaction["action"]["arguments"]["transfers"]:
                                ESDTvalue = int(transfer["value"])
                                try:
                                    ticker = transfer["token"]
                                except KeyError:
                                    ticker = transfer["ticker"]
                                writetx("Erverv", ESDTvalue, ticker, 0, "", 0, \
                                        name + ", Regular transfer in. Sender: " + transaction["sender"])
                ### No action field:
                else:
                    if transaction["type"] == "SmartContractResult":
                        originaltxhash = transaction["originalTxHash"]
                        fulltx = getURL(APIaddress + "/transactions/" + originaltxhash).json()
                        function = fulltx["function"]
                        if function in ["buy", "buyNft", "mint", "enterSale"]:
                            Tokenssent, Tokensreceived = getTokens(fulltx)
                            {
                              "buy": getNFT,
                              "buyNft": getNFT,
                              "mint": getNFT,
                              "enterSale": getNFT
                              }[function](function, 0, transaction, fulltx, Tokenssent, Tokensreceived)
                        else:
                            undefined_tx(function, 0, transaction, fulltx, Tokenssent, Tokensreceived)
                    if transactionid not in registeredfees:
                        eGLDvalue = int(transaction["value"])
                        if transaction["sender"] not in ownWalletlist:
                            writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", 0,
                                    "Regular transfer in. Sender: " + transaction["sender"])
                        else:
                            writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", 0,
                                    "transfer between own wallets")
            else:
                ### Try to read the action field.
                if transaction["type"] == "Transaction":
                    fulltx = getURL(APIaddress + "/transactions/" + transactionid).json()
                    ### Make an overview of what has gone in & what has gone out.
                    Tokenssent, Tokensreceived = getTokens(fulltx)
                    name = transaction["action"]["name"]
                    try:
                        {
                         "transfer": Transfer
                         }[name](name, 0, transaction, fulltx, Tokenssent, Tokensreceived)
                    except KeyError:
                        undefined_tx(name, 0, transaction, fulltx, Tokenssent, Tokensreceived)
                else:
                    print("unknown TX, skipped: " + transactionid)

def getTokens(fulltx):
    Tokenssent = {}
    Tokensreceived = {}
    if "operations" in fulltx:
        for operation in fulltx["operations"]:
            operation["sender"] = AliasSwap(operation, "sender")
            operation["receiver"] = AliasSwap(operation, "receiver")
            if operation["action"] == "transfer":
                try:
                    ticker = operation["identifier"]
                except KeyError:
                    ticker = "EGLD"
                if len(ticker.split("-")) > 2:
                    ticker = ticker.split("-")[0] + "-" + ticker.split("-")[1]
                ESDTvalue = int(operation["value"])
                if operation["receiver"] == wallet_address and \
                   ticker != "EGLD":
                    if ticker not in Tokensreceived:
                        Tokensreceived[ticker] = ESDTvalue
                    else:
                        n = 0
                        newtick = ticker
                        while newtick in Tokensreceived:
                            print("Found duplicate! " + newtick)
                            n += 1
                            newtick = ticker + "_" + str(n)
                        ticker = newtick
                        Tokensreceived[ticker] = ESDTvalue
                elif operation["receiver"] == wallet_address:
                    if ticker not in Tokensreceived:
                        Tokensreceived[ticker] = ESDTvalue
                    else: Tokensreceived[ticker] += ESDTvalue
                if operation["sender"] == wallet_address:
                    if ticker not in Tokenssent:
                        Tokenssent[ticker] = ESDTvalue
                    else: Tokenssent[ticker] += ESDTvalue
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
    writetx("Handel", eGLDvalue, ticker, eGLDvalue, "EGLD", fee, name)
    
def unwrapEgld(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """unwrapEgld == handel"""
    for transfer in transaction["action"]["arguments"]["transfers"]:
        eGLDvalue = int(transfer["value"])
        ticker = transfer["ticker"]
        writetx("Handel", eGLDvalue, "EGLD", eGLDvalue, ticker, fee, name)

def unStake(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """unStaking (legacy)"""
    for result in fulltx["results"]:
        if fulltx["receiver"] == wallet_address:
            eGLDvalue = int(result["value"])
            writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "", fee, name)

def reDelegateRewards(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """reDelegating"""
    for result in fulltx["results"]:
        if result["receiver"] == wallet_address:
            eGLDvalue = int(result["value"])
            writetx("Inntekt", eGLDvalue, "EGLD", 0, "EGLD", fee, name)

def claimLockedAssets(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """claim first LKMEX batch == inntekt"""
    for operation in fulltx["operations"]:
        if operation["action"] == "transfer":
            ticker = "LKMEX-aab910"
            ESDTvalue = int(operation["value"])
            writetx("Inntekt", ESDTvalue, ticker, 0, "EGLD", fee, name)

### Needs re-write, as RIDE is not the only launchpad token any longer.
def claimLaunchpadTokens(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """claim Launchpad tokens. Claim == inntekt"""
    for operation in fulltx["operations"]:
        if operation["type"] == "egld":
            eGLDvalue = int(operation["value"])
            writetx("Overføring-Inn", eGLDvalue, "EGLD", 0, "EGLD", fee, name)
        elif operation["type"] == "esdt":
            ticker = list(Tokensreceived.keys())[0]
            ESDTvalue = int(operation["value"])
            writetx("Handel", ESDTvalue, ticker, (ESDTvalue / 5000) * 0.47, "EGLD", fee, name)

def addLiquidity(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Add liquidity = Handel. Anything extra = Inntekt (LKMEX/XMEX rewards)"""
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
    """Removing liquidity = Handel. Anything extra = Inntekt (LKMEX/XMEX rewards)"""
    mainticker = list(Tokenssent.keys())[0]
    firsttoken = list(Tokensreceived.keys())[0]
    secondtoken = list(Tokensreceived.keys())[1]
    writetx("Handel", Tokensreceived[firsttoken], firsttoken,
                Tokenssent[mainticker] / 2,
                mainticker, fee,
                name)
    writetx("Handel", Tokensreceived[secondtoken], secondtoken,
                Tokenssent[mainticker] / 2,
                mainticker, fee,
                name)
    del Tokensreceived[firsttoken]
    del Tokensreceived[secondtoken]
    for key in Tokensreceived.keys():
        writetx("Inntekt", Tokensreceived[key], key, 0, "", fee, name)
    del Tokenssent[mainticker]
    for key in Tokenssent.keys():
        writetx("Overføring-Ut", Tokenssent[key], key, 0, "", fee, name)

def compoundRewards(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Compounding rewards = Erverv (we're not going to attach any value to them now)"""
    for key in Tokenssent.keys():
        if key in Tokensreceived.keys():
            difference = Tokensreceived[key] - Tokenssent[key]
            del Tokensreceived[key]
            if difference > 0:
                writetx("Erverv", difference, key, 0, "", fee, name)
        else:
            ### Anything else we don't know or care. Overføring ut.
            writetx("Overføring-Ut", 0, "", Tokenssent[key], key, fee, name)
    for key in Tokensreceived.keys():
        writetx("Erverv", Tokensreceived[key], key, 0, "", fee, name)

def enterFarm(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Entering the farm = Handel. Anything extra = Erverv"""
    topreceived = list(Tokensreceived.keys())[0]
    for key in Tokensreceived.keys():
        ### When we enter a farm it can be that we already staked to that farm.
        ### In that case, Elrond will send us a sum of all tokens, including the new ones we put in.
        if key in Tokenssent.keys():
            difference = Tokensreceived[key] - Tokenssent[key]
            Tokensreceived[key] = difference
            del Tokenssent[key]
    for key in Tokenssent.keys():
        ### For each token we sent, 
        writetx("Handel", Tokensreceived[topreceived]/len(Tokenssent.keys()), \
                topreceived, Tokenssent[key], key, fee, name)
    del Tokensreceived[topreceived]
    for key in Tokensreceived.keys():
        writetx("Erverv", Tokensreceived[key], key, 0, "", fee, name)

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
            writetx("Handel", Tokensreceived[topreceived]/len(Tokenssent.keys()), \
                    topreceived, Tokenssent[key], key, fee, name)
        del Tokensreceived[topreceived]
        deleted = True
    try:
        if deleted:
            ### The transfer (if any) are rewards. Treat as Inntekt
            writetx("Inntekt", list(Tokensreceived.values())[0], \
                    list(Tokensreceived.keys())[0], 0, "", fee, name)
        else:
            ### The first transfer is our own tokens. Treat as Overføring-Inn
            writetx("Overføring-Inn", list(Tokensreceived.values())[0], \
                    list(Tokensreceived.keys())[0], 0, "", fee, name)
            ### The second transfer (if any) is rewards. Treat as Inntekt
            writetx("Inntekt", list(Tokensreceived.values())[1], \
                    list(Tokensreceived.keys())[1], 0, "", fee, name)
    except IndexError:
        pass

def swap(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Swapping = Handel. Use also when migrating to new farm."""
    if name == "swap":
        swapout = transaction["action"]["arguments"]["transfers"][0]["token"]
        swapin = transaction["action"]["arguments"]["transfers"][1]["token"]
    if name == "transfer":
        swapout = list(Tokenssent)[0]
        swapin = list(Tokensreceived)[0]
    #swapout = swapout.split("-")[0]
    #swapin = swapin.split("-")[0]
    writetx("Handel", Tokensreceived[swapin], swapin, \
            Tokenssent[swapout], swapout, fee, name)
    del Tokensreceived[swapin]
    del Tokenssent[swapout]
    for key in Tokenssent.keys():
        writetx("Inntekt", Tokenssent[key], key, 0, "", fee, name)
    for key in Tokensreceived.keys():
        writetx("Inntekt", Tokensreceived[key], key, 0, "", fee, name)

def claimRewards(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Claiming rewards. If EGLD, Inntekt. Otherwise Erverv"""
    for key in Tokenssent.keys():
        if key in Tokensreceived.keys():
            difference = Tokenssent[key] - Tokensreceived[key]
            del Tokensreceived[key]
            if difference > 0:
                writetx("Tap-uten-fradrag", 0, "", difference, key, fee, name)
    for key in Tokensreceived.keys():
        if key == "EGLD":
              writetx("Inntekt", Tokensreceived[key], key, 0, "", fee, name)
        else:
            writetx("Erverv", Tokensreceived[key], key, 0, "", fee, name)

def getNFT(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Getting NFT's. Through Handel."""
    ### First option is that we're buying an NFT.
    if "EGLD" not in Tokensreceived:
        EGLDvalue = float(fulltx["value"])
        tr = {list(Tokensreceived)[0]:0.0}
        for key in Tokensreceived.keys():
            tr[key.split("_")[0]] += Tokensreceived[key]
        for key in Tokensreceived.keys():
            writetx("Handel",  Tokensreceived[key], key, EGLDvalue/len(Tokensreceived.keys()), "EGLD", fee, name + " at " + transaction["receiver"])
    ### Second option is that we're selling an NFT, and receiving EGLD for it.
    else:
        ### First we're finding out which NFT(s) we've sold
        for operation in fulltx["operations"]:
            if operation["type"] == "nft":
                Tokenssent[operation["collection"]] = operation["value"]
        ### Secondly, we write it as a Handel
        EGLDvalue = Tokensreceived[list(Tokensreceived.keys())[0]]
        for key in Tokenssent.keys():
            writetx("Handel",  EGLDvalue/len(Tokenssent.keys()), "EGLD", Tokenssent[key], key,  fee, "sellNft at " + transaction["sender"])

def Transfer(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    sender = ""
    receiver = ""
    for operation in fulltx["operations"]:
        operation["sender"] = AliasSwap(operation, "sender")
        operation["receiver"] = AliasSwap(operation, "receiver")
        if operation["action"] == "transfer":
            if operation["sender"] == wallet_address: receiver = operation["receiver"]
            elif operation["receiver"] == wallet_address: sender = operation["sender"]
    ### Filter the transfer items to only show NFT's.
    doubletransfers = ["MEX", "LKMEX", "XMEX", "LKFARM", "WEGLD", "LKLP", "MEXFARM", "MEXFARML"]
    for key in Tokensreceived.keys():
        if sender not in ownWalletlist and \
            key.split("-")[0] not in doubletransfers:
            writetx("Erverv", Tokensreceived[key], key, 0, "", fee, name + " from " + sender)
        else:
            writetx("Overføring-Inn", Tokensreceived[key], key, 0, "", fee, name + " from " + sender)
    for key in Tokenssent.keys():
        if receiver == "Burn Wallet":
            writetx("Overføring-Ut", 0, "", 0, "", fee, name + " to " + receiver + " fee")
            writetx("Tap", 0, "", Tokenssent[key], key, 0, name + " to " + receiver)
        elif receiver not in ownWalletlist and \
            key.split("-")[0] not in doubletransfers:
            writetx("Overføring-Ut", 0, "", Tokenssent[key], key, fee, name + " to " + receiver)
        elif key.split("-")[0] not in doubletransfers:
            writetx("Overføring-Ut", 0, "", Tokenssent[key], key, fee, "transfer between own wallets")

def undefined_tx(name, fee, transaction, fulltx, Tokenssent, Tokensreceived):
    """Anything undefined"""
    function = ""
    if "function" in transaction:
        function = transaction["function"]
    print("Not Defined: " + name + ". Function: " + function + ". ID: " + transactionid)
    for key in Tokensreceived.keys():
        writetx("Overføring-Inn", Tokensreceived[key], key, 0, "", fee, "Not Recognized: " + name + ". Function: " + function)
    for key in Tokenssent.keys():
        writetx("Overføring-Ut", 0, "", Tokenssent[key], key, fee, "Not Recognized: " + name + ". Hash: " + function)

            
if __name__ == "__main__":
    #getPriceData("MEX-455c57", "2021-11-24")
    csvparser()
