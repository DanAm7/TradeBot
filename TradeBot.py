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
	TotalEarn = 0  # Reset total earn	
	TotalSpend = 0 # Reset total spend
	id = 0 # Reset id index
	FirstRun = True # Set first run true
	PrintFlag = False #Set Print run off
	OpenBuyOrdersID_list = [] # Set empty open buy order list
	MarketsWithOpenOrders = [] # Set an empty for all tokens we already had pending order for
	BitcoinPrice = float(request('GET', '/exchange/api/v2/info/prices', '', None).get('BTCUSDC')) # Get Bitcoin price from web
	BP_fixed_USD = float(input('Position Price in USD: ')) # Asking for position price in USD
	Ans = input('Conver all to BTC? (y/n): ') #Asking to convert all tokens back to BTC
	while True: # Program reset finished - Main loop start
	#try:
		BitcoinPrice = float(request('GET', '/exchange/api/v2/info/prices', '', None).get('BTCUSDC')) # Update BTC price
		BP_fixed = BP_fixed_USD/BitcoinPrice # Set the amount of BTC for position after BTC price in USD update
		MarketDic = request('GET', '/exchange/api/v2/info/prices', '', None) # Getting Dic of all markets
		Market_List = MarketDic.keys() # Create a list with all market names from MarketDic
		if FirstRun and Ans == 'y': # Check if first run and Sell all
			FirstRun = False # Set FirstRun flag to false
			for Market in Market_List: # Starting a loop the check every market name in market names list
				if 'BTC' in str(Market)[3:]: # Check if to market is token against BTC
					res = request('DELET', '/exchange/api/v2/info/cancelAllOrders', 'market='+Market+'&side=BUY', None) # Canceling all pending orders for the token
					Avilable = request('GET', '/main/api/v2/accounting/account2/'+str(Market).replace('BTC',''), '', None) # Get the avilable amount of token in wallet
					Avilable = float(Avilable.get('available')) # Convert value to float
					if Avilable > 0.0001: # Check if there is from the corrunt token in wallet
						res = request('POST', '/exchange/api/v2/order', 'market='+str(Market)+'&side=SELL&type=MARKET&quantity=' + str(Avilable) , None) # Selling remaining token in wallet
						print(colored('Sell for reste ', 'magenta')+str(Market)) # Print
						print(res) # Print Details
		for key in Market_List: # Starting a loop the check every market name in market names list
			if 'BTC' in str(key)[3:]: # Check if to market is token against BTC
				Market = str(key) # Set market name str
				MarketPrice = float(MarketDic.get(key)) # Getting the price of the token
				MarketOrderList = request('GET', '/exchange/api/v2/info/myOrders/', 'market='+Market, None) # Get list of all orders of the token
				for Order in MarketOrderList: # Loop of all orders
					if Order.get('state') != 'FULL': # Check if order is open
						ThereIsOrder = True # Set the ThereIsOrder flag to true for marking there is already peanding order for the token
					else:
						ThereIsOrder = False # Set the ThereIsOrder flag to false for marking there is no peanding order for the token

					if Order.get('id') in OpenBuyOrdersID_list and Order.get('state') == 'FULL': # Check if the order id is in the open buy order list and if order is complited
						OpenBuyOrdersID_list.remove(Order.get('orderId')) # Removing the order from the open but order list
						SecQuantity = Decimal(BP_fixed/MarketPrice) # Set the price in btc to pay for the token
						PriceLimit = (float(Order.get('price'))*1.03) # set the price limit fot he sell order for 3% from the buy price
						print(colored('Open sell order', 'yellow') + Market) # Print
						res = request('POST', '/exchange/api/v2/order', 'market='+Market+'&side=SELL&type=LIMIT&quantity='+str(SecQuantity)+'&price='+PriceLimit , None) # Open sell order
						print(res) # Print details

					if not ThereIsOrder and not Market in MarketsWithOpenOrders: # Check if there is no open orders of the token in buy orders list and the token is not in the list of open orders
						AVG = CalculateAVG(Market) # Calculating Avrege of the previos 48 hours
						MarketDic = request('GET', '/exchange/api/v2/info/prices', '', None) # Update Data
						MarketPrice = float(MarketDic.get(key)) # Update market price
						if MarketPrice > AVG: # Check if to buy
							quantity = str(Decimal(BP_fixed/MarketPrice)) # Set the price in btc to pay for the token
							print(colored('Open Buy order -- ', 'red')+Market) # Print
							res = request('POST', '/exchange/api/v2/order', 'market='+Market+'&side=BUY&type=LIMIT&quantity='+quantity+'&price='+str(MarketPrice), None) # Open buy order fot token
							print(res) # Print details 
							if res != False: # Check if order open sucssefully
								OpenBuyOrdersID_list.append(res.get('orderId')) # Add open order to list
								MarketsWithOpenOrders.append(Market) # Add open order to list
						###################################################################################################	time.sleep(30)





								TotalEarn = TotalEarn + float(Obj.Quantity)*MarketPrice
								Market = Obj.Market
								res = request('POST', '/exchange/api/v2/order', 'market='+str(Market)+'&side=SELL&type=MARKET&quantity=' + str(Avilable) , None)
								print(res)
								if res != False:
									Positions_list.remove(Obj)
									print(GetTime()+colored('Sell', 'green')+' Coin: ' +str(Obj.Market).replace('BTC','') +' Buy Price: '+str(Decimal(Obj.BuyPrice))[:10]+' Price: ' + str(Decimal(MarketPrice))[:10] +' Profit(%): '+colored(str(Decimal(Profit))[:5], 'blue') +' Positions Count: '+str(len(Positions_list))+ ' Total Spend: '+colored(str(TotalSpend)[:10], 'yellow')+ ' Total Earn: '+colored(str(TotalEarn)[:10], 'cyan'))
									PrintFlag = True
					AVG = CalculateAVG(Market)
					MarketDic = request('GET', '/exchange/api/v2/info/prices', '', None)
					MarketPrice = float(MarketDic.get(key))
					if MarketPrice < AVG:
						NewPos_flag = True
						for Pos in Positions_list:
							if str(Pos.Market) == str(Market):
								NewPos_flag = False
						if NewPos_flag:
							TotalSpend = TotalSpend + BP_fixed
							Quantity = BP_fixed
							SecQuantity = Decimal(Quantity/MarketPrice)
							res = request('POST', '/exchange/api/v2/order', 'market='+str(Market)+'&side=BUY&secQuantity='+str(Decimal(Quantity))[:15]+'&type=MARKET&quantity='+str(SecQuantity)[:15]  , None)
							print(res)
							if res != False:
								New_Position = Position(id, Market, MarketPrice, SecQuantity, MarketPrice*0.5)
								AVG_prec = 100 - ((MarketPrice/AVG)*100)
								id += 1
								Positions_list.append(New_Position)
								print(GetTime()+ colored('Buy', 'red')+' Coin: ' +colored(str(New_Position.Market).replace('BTC',''), 'blue') +' Price: ' + str(Decimal(New_Position.BuyPrice))[:10] +' AVG: '+str(Decimal(AVG))[:10] +' Avg Precenteg(%): '+str(AVG_prec)[:5]+' Positions Count: '+ str(len(Positions_list))+' Total Spend: '+colored(str(TotalSpend)[:10], 'yellow')+ ' Total Earn: '+colored(str(TotalEarn)[:10], 'cyan'))
								PrintFlag = True
			# for Obj in Positions_list:
			#     print(colored('Checking Position: ','yellow')+str(Obj.Market).replace('BTC','')+' Buy Price: '+str(Obj.BuyPrice)+' Current Price: '+str(Decimal(MarketPrice))[:10]+ ' Profability(%): '+str())
			if PrintFlag:
				PrintFlag = False
				print_list = []
				for Obj in Positions_list:
					print_list.append(str(Obj.Market.replace('BTC','')))
				print(' ')
				print(print_list)
			time.sleep(30)
		# except:
		#     print('Generic Error...')
		#     time.sleep(30)

MainFunc()

