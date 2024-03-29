#!/usr/bin/python3
import bluetooth
from Adafruit_IO import Client, Feed
from twilio.rest import Client as TwilioClient
from datetime import datetime
import logging

logging.basicConfig(filename='src/aq_monitor.log',level=logging.INFO,
                    format = '%(asctime)s %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

# AQ Monitor collects 15 second averages and posts them to AIO
# Will send a text if any single reading (of the 15) is too high
#			- AQ SMS is responsible for responding to incoming texts

# Data to send to Adafruit IO Feeds
temp = hum = pm10 = pm25 = tvoc = co = co2 = None

# Bluetooth Settings
bt_addr = '00:14:03:06:10:BB'
port = 1
connection_data = (bt_addr, port)
socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
socket.connect(connection_data)
# Parsing Incoming Bytes
found_begin = False
data_begin = '<'
data_end = '>'
data = ''

twilio_num = None
my_num = None
TWIL_SID = None
TWIL_TOKEN = None
alert_temp = alert_hum = alert_tvoc = alert_co = alert_co2 = False
postsFailed = 0
key_file = 'src/keys.txt'
# Adafruit IO
ADAFRUIT_IO_USERNAME = None
ADAFRUIT_IO_KEY = None 
# My feeds
temp_feed = None
hum_feed = None
pm10_feed = None
pm25_feed = None
tvoc_feed = None
co_feed = None
co2_feed = None

logging.info('Starting AQ Monitor')

try:
    with open(key_file) as f:
        content = f.readlines()
        content = [x.strip() for x in content]
        f.close()
except:
    logging.error("Could not load info from keys.txt.")
else:
	try:
		twilio_num = content[0]
		my_num = content[1]
		TWIL_SID = content[2]
		TWIL_TOKEN = content[3]
		ADAFRUIT_IO_USERNAME = content[4]
		ADAFRUIT_IO_KEY = content[5]
	except:
		logging.error('Error: Could not get keys from keys.txt')
	else:
		# Only run after loading keys
		try:
			twil_client = TwilioClient(TWIL_SID, TWIL_TOKEN)
		except:
			logging.error('Could not start Twilio Client. Check keys\nExiting.')
			exit()
		else:
			logging.info('Twilio Client successfully created...')
		try:
			aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
		except:
			logging.error('Could not start Adafruit IO Client. Check keys\nExiting')
			exit()
		else:
			logging.info('AIO Client successfully created...')
			try:
				temp_feed = aio.feeds('arduino-air-quality-monitor.temperature')
				hum_feed = aio.feeds('arduino-air-quality-monitor.humidity')
				pm10_feed = aio.feeds('arduino-air-quality-monitor.pm10')
				pm25_feed = aio.feeds('arduino-air-quality-monitor.pm25')
				tvoc_feed = aio.feeds('arduino-air-quality-monitor.tvoc')
				co_feed = aio.feeds('arduino-air-quality-monitor.co')
				co2_feed = aio.feeds('arduino-air-quality-monitor.co2')
			except:
				logging.error('Error loading AIO feeds')
				exit()
			else:
				logging.info('Loaded AIO feeds successfully...')


################################################################################
# Helper Functions

# Sends warning texts to personal number specified\
def sendAlert(msg):
	try:
		twil_client.messages.create(to=my_num,from_=twilio_num, body=msg)
	except:
		logging.error('Could not send sms. Check sendAlert')

def checkReadings(temp, hum, tvoc, co, co2):
	global alert_temp, alert_hum, alert_tvoc, alert_co, alert_co2
	if float(temp) > 82.0 and alert_temp == False:
		sendAlert('Air Quality Alert:\nTemperature has exceeded ' +temp+ ' degrees')
		alert_temp = True
	elif float(temp) < 75.0 and alert_temp == True:
		sendAlert('Air Quality Alert:\nTemperature dropped to ' +temp+ ' degrees')
		alert_temp = False
	if float(hum) > 60.0 and alert_hum == False:
		sendAlert('Air Quality Alert:\nHumidity has exceeded ' + hum + '%')
		alert_hum = True
	elif float(hum) < 50.0 and alert_hum == True:
		sendAlert('Air Quality Alert:\nHumidity dropped to ' +hum+ '%')
		alert_hum = False
	if int(tvoc) > 35 and alert_tvoc == False:
		sendAlert('Air Quality Alert:\nTVOC has exceeded ' + tvoc + ' ppm')
		alert_tvoc = True 
	elif int(tvoc) < 10 and alert_tvoc == True:
		sendAlert('Air Quality Alert:\nTVOC has dropped to ' + tvoc + ' ppm')
		alert_tvoc = False
	if float(co) > 24.99 and alert_c0 == False:
		sendAlert('Air Quality Alert:\nCO has exceeded ' + co + ' ppm')
		alert_co = True
	elif float(co) < 25.0 and alert_co == True:
		sendAlert('Air Quality Alert:\nTVOC has dropped to ' + co + ' ppm')
		alert_co = False
	if int(co2) > 900 and alert_co2 == False:
		sendAlert('Air Quality Alert:\nCO2 has exceeded ' + co2 + ' ppm')
		alert_co2 = True
	elif int(co2) < 600 and alert_co2 == True:
		sendAlert('Air Quality Alert:\nCO2 has dropped to ' + co2 + ' ppm')
		alert_co2 = False
	
# Recieves byte-string from Bluetooth socket
# Parses the data and sends to AIO feeds
def post(data):
	global postsFailed
# Send
	try:
		aio.send(temp_feed.key, str(data[0]))
		aio.send(hum_feed.key, str(data[1]))
		aio.send(pm10_feed.key, str(data[2]))
		aio.send(pm25_feed.key, str(data[3]))
		aio.send(tvoc_feed.key, str(data[4]))
		aio.send(co_feed.key, str(data[5]))
		aio.send(co2_feed.key, str(data[6]))
	except: #TODO send text if aio_error_sent is false, set true after
		postsFailed += 1
		logging.error("Failed to post to AIO. Not parsing error. Probably trying "
						f"again in a few seconds. Error Num: {postsFailed}")
		if postsFailed == 1 or postsFailed == 10 or postsFailed == 100:
			sendAlert(f"Air Quality Alert:\nFailed to post to AIO.\n{postsFailed} consecutive fails.")
	else:
		if postsFailed > 0:
			sendAlert(f'AQ back online after {postsFailed} failed attempts')
		postsFailed = 0

################################################################################
# Take 15 loop average, then post
temp_t = 0
hum_t = 0
pm10_t = 0
pm25_t = 0
tvoc_t = 0
co_t = 0
co2_t = 0
data_to_post = []
i = 0
data = ''
while 1:
		try:
			bytes = socket.recv(1024)
			if len(bytes) == 0: break
			else:
					data += str(bytes).strip("\'b\'")
					if found_begin is False:
						begin_index = data.find(data_begin)
						if begin_index != -1:
							data = data[begin_index + 1:]
							found_begin = True
					if found_begin:
						end_index = data.find(data_end)
						if end_index != -1: # Found new data set
							try:
								data = data[:end_index]
								data = data.split(',')
							except:
								logging.warning('Failed to parse incoming data')
							else:
								temp_t += float(data[0])
								hum_t += float(data[1])
								pm10_t += float(data[2])
								pm25_t += float(data[3])
								tvoc_t += float(data[4])
								co_t += float(data[5])
								co2_t += float(data[6])
								data = ''
								i += 1
								found_begin = False
						if i == 14:
							data_to_post.append(round((float(temp_t)/i), 3))
							data_to_post.append(round((float(hum_t)/i), 3))
							data_to_post.append(round((float(pm10_t)/i), 3))
							data_to_post.append(round((float(pm25_t)/i), 3))
							data_to_post.append(round((float(tvoc_t)/i), 3))
							data_to_post.append(round((float(co_t)/i), 3))
							data_to_post.append(round((float(co2_t)/i), 3))
							#for data_t in data_to_post:
							#	print(data_t)
							#print('\n')
							post(data_to_post)
							data_to_post.clear()
							temp_t = 0
							hum_t = 0
							pm10_t = 0
							pm25_t = 0
							tvoc_t = 0
							co_t = 0
							co2_t = 0
							i = 0
							data = ''
			
		except IOError:
			pass
	
		except KeyboardInterrupt:
			logging.info('\nClosing connection...')
			socket.close()
			logging.info('Done.')
			break
