import requests
import time
import uuid
import hmac
from hashlib import sha256
from datetime import datetime
import json
from decimal import Decimal
from termcolor import colored


API_Org_ID = "f0e611d7-3d56-474c-bb51-5d414298636c"
API_Key = "00ccecd9-3853-4859-b97b-027fddd4f130"
API_Secret = "24ae3008-4482-4bba-968c-908e9ff8e523a8934871-8842-4803-a2de-4abe8afdcddd"
host = 'https://api2.nicehash.com'

global Positions_list
global id
Positions_list = []


def get_ts():
    now = datetime.now()
    now_ec_since_epoch = time.mktime(now.timetuple()) + now.microsecond / 1000000.0
    return str(int(now_ec_since_epoch * 1000))

def GetTime():
    return str(datetime.now().strftime("%H:%M:%S") + ' ' + '-' + ' ')

def GetPreviusTS(k):
    return int(time.time() - k * 3600)

def request(method, path, query, body):
    while True:
        try:

            xtime = get_ts()
            xnonce = str(uuid.uuid4())

            message = bytearray(API_Key, 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray(xtime, 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray(xnonce, 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray(API_Org_ID, 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray(method, 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray(path, 'utf-8')
            message += bytearray('\x00', 'utf-8')
            message += bytearray(query, 'utf-8')

            if body:
                body_json = json.dumps(body)
                message += bytearray('\x00', 'utf-8')
                message += bytearray(body_json, 'utf-8')

            digest = hmac.new(bytearray(API_Secret, 'utf-8'), message, sha256).hexdigest()
            xauth = API_Key + ":" + digest

            headers = {
                'X-Time': xtime,
                'X-Nonce': xnonce,
                'X-Auth': xauth,
                'Content-Type': 'application/json',
                'X-Organization-Id': API_Org_ID,
                'X-Request-Id': str(uuid.uuid4())
            }
            
            s = requests.Session()
            s.headers = headers

            url = host + path
            if query:
                url += '?' + query

            if body:
                response = s.request(method, url, data=body_json)
            else:
                response = s.request(method, url)

            if response.status_code == 200:
                return response.json()
            elif response.content:
                print(str(response.status_code) + ": " + response.reason + ": " + str(response.content))
                return False
            else:
                print(str(response.status_code) + ": " + response.reason)
                return False
        except:
            print(colored('Request Error!', 'red'))
            time.sleep(10)

def CalculateAVG(Market):
    sum = 0
    n = 0
    candlesticks_list = request('GET', '/exchange/api/v2/info/candlesticks', 'market='+str(Market)+'&from='+str(GetPreviusTS(48))+'&resolution=1&to='+str(int(time.time())), None)
    if not candlesticks_list:
        return 0
    for candle in candlesticks_list:
        open = float(candle.get('open'))
        close = float(candle.get('close'))
        sum = sum + ((close+open)/2)
        n += 1
    return float(sum/n)

def MainFunc():
    global Positions_list
    TotalEarn = 0
    TotalSpend = 0
    id = 0
    FirstRun = True
    PrintFlag = False
    OpenBuyOrdersID_list = []
    MarketsWithOpenOrders = []
    BitcoinPrice = float(request('GET', '/exchange/api/v2/info/prices', '', None).get('BTCUSDC'))
    BP_fixed_USD = float(input('Position Price in USD: '))
    Ans = input('Conver all to BTC? (y/n): ')
    while True:
    #    try:
    	BitcoinPrice = float(request('GET', '/exchange/api/v2/info/prices', '', None).get('BTCUSDC'))
    	BP_fixed = BP_fixed_USD/BitcoinPrice
    	MarketDic = request('GET', '/exchange/api/v2/info/prices', '', None)	
    	Market_List = MarketDic.keys()
    	if FirstRun and Ans == 'y':
    		FirstRun = False
    		for Market in Market_List:
    			if 'BTC' in str(Market)[3:]:
    				res = request('DELET', '/exchange/api/v2/info/cancelAllOrders', 'market='+Market+'&side=BUY', None)
    				Avilable = request('GET', '/main/api/v2/accounting/account2/'+str(Market).replace('BTC',''), '', None)
    				Avilable = float(Avilable.get('available'))
    				if Avilable > 0.0001:
    					res = request('POST', '/exchange/api/v2/order', 'market='+str(Market)+'&side=SELL&type=MARKET&quantity=' + str(Avilable) , None)
    					print(colored('Sell for reste ', 'magenta')+str(Market))
    					print(res)
    	for key in Market_List:
    		if 'BTC' in str(key)[3:]:
    			Market = str(key)
    			MarketPrice = float(MarketDic.get(key))
    			MarketOrderList = request('GET', '/exchange/api/v2/info/myOrders/', 'market='+Market, None)
    			for Order in MarketOrderList:
    				if Order.get('state') != 'FULL':
    					ThereIsOrder = True
    				else:
    					ThereIsOrder = False
    				if Order.get('id') in OpenBuyOrdersID_list and Order.get('state') == 'FULL':
    					OpenBuyOrdersID_list.remove(Order.get('orderId'))
    					SecQuantity = Decimal(BP_fixed/MarketPrice)
    					PriceLimit = (float(Order.get('price'))*1.03)
    					print(colored('Open sell order', 'green') + Market)
    					res = request('POST', '/exchange/api/v2/order', 'market='+Market+'&side=SELL&type=LIMIT&quantity='+str(SecQuantity)+'&price='+PriceLimit , None)
    					print(res)
    				if not ThereIsOrder and not Market in MarketsWithOpenOrders:
    					AVG = CalculateAVG(Market)
    					MarketDic = request('GET', '/exchange/api/v2/info/prices', '', None)
    					MarketPrice = float(MarketDic.get(key))
    					if MarketPrice < AVG:
    						quantity = str(Decimal(BP_fixed/MarketPrice))
    						print(colored('Open Buy order -- ', 'red')+Market)
    						res = request('POST', '/exchange/api/v2/order', 'market='+Market+'&side=BUY&type=LIMIT&quantity='+quantity+'&price='+str(MarketPrice), None)
    						print(res)
    						if res != False:
    							OpenBuyOrdersID_list.append(res.get('orderId'))
    							MarketsWithOpenOrders.append(Market)
    	time.sleep(30)

MainFunc()
