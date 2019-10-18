#!/usr/bin/python3
import bluetooth
from flask import Flask, request
from Adafruit_IO import Client, Feed
from twilio import twiml
from twilio.rest import Client as TwilioClient
from datetime import datetime

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
#TwilioClient(TWIL_SID, TWIL_TOKEN)
alert_log = 'log.txt'
key_file = 'keys.txt'
# Adafruit IO
ADAFRUIT_IO_USERNAME = None
ADAFRUIT_IO_KEY = None 
#Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
# My feeds
temp_feed = None
hum_feed = None
pm10_feed = None
pm25_feed = None
tvoc_feed = None
co_feed = None
co2_feed = None

print('Starting AQ Monitor...')

app = Flask(__name__)

@app.route('/sms', methods=['POST'])
def sms():
	number = request.form['From']
	message_body = request.form['Body']
	resp = twiml.Response()
	resp.message('Hello {}, you said: {}' .format(number, message_body))
	return str(resp)



try:
    with open(key_file) as f:
        content = f.readlines()
        content = [x.strip() for x in content]
        f.close()
except:
    print("Could not load info from keys.txt.")
else:
	try:
		  twilio_num = content[0]
	except:
		  print('Error: Could not get Twilio phone number from keys.txt')
	try:
		  my_num = content[1]
	except:
		  print('Error: Could not get personal number from keys.txt')
	try:
		  TWIL_SID = content[2]
	except:
		  print('Error: Could not get Twilio SID from keys.txt')
	try:
		  TWIL_TOKEN = content[3]
	except:
		  print('Error: Could not get Twilio Token from keys.txt')
	try:
		  ADAFRUIT_IO_USERNAME = content[4]
	except:
		  print('Error: Could not get AIO username from keys.txt')
	try:
		  ADAFRUIT_IO_KEY = content[5]
	except:
		   print('Error: Could not get AIO key from keys.txt')
	else:
		# Only run after loading keys
		try:
			twil_client = TwilioClient(TWIL_SID, TWIL_TOKEN)
		except:
			print('Could not start Twilio Client. Check keys')
			exit()
		else:
			print('Twilio Client successfully created...')
		try:
			aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
		except:
			print('Could not start Adafruit IO Client. Check keys')
			exit()
		else:
			print('AIO Client successfully created...')
			try:
				temp_feed = aio.feeds('arduino-air-quality-monitor.temperature')
				hum_feed = aio.feeds('arduino-air-quality-monitor.humidity')
				pm10_feed = aio.feeds('arduino-air-quality-monitor.pm10')
				pm25_feed = aio.feeds('arduino-air-quality-monitor.pm25')
				tvoc_feed = aio.feeds('arduino-air-quality-monitor.tvoc')
				co_feed = aio.feeds('arduino-air-quality-monitor.co')
				co2_feed = aio.feeds('arduino-air-quality-monitor.co2')
			except:
				print('Error loading AIO feeds')
				exit()
			else:
				print('Loaded AIO feeds successfully...')
     

################################################################################
# Helper Functions

# Adds entry in log when there is an alert
def addLogEntry(alert):
	now = datetime.now()
	timestamp = now.strftime("%m/%d/%Y %H:%M:%S")
	with open(alert_log, 'a+') as log_file:
		log_file.write(str(timestamp) + ': ' + alert)
	log_file.close()


# Sends warning texts to personal number specified\
def sendAlert(msg):
	twil_client.messages.create(to=my_num,from_=twilio_num,
															body=msg)
	#print('AQ Alert sent: %s' % msg)
	addLogEntry(msg[19:] + '\n')

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
def parseAndPost(data):
	# Parse
	try:
		data_list = data.split(',')
		temp = data_list[0]
		hum = data_list[1]
		pm10 = data_list[2]
		pm25 = data_list[3]
		tvoc = data_list[4]
		co = data_list[5]
		co2 = data_list[6]
		checkReadings(temp, hum, tvoc, co, co2)
	except IOError: # Give it a few tries
		pass
	# Send
	try:
		aio.send(temp_feed.key, str(temp))
		aio.send(hum_feed.key, str(hum))
		aio.send(pm10_feed.key, str(pm10))
		aio.send(pm25_feed.key, str(pm25))
		aio.send(tvoc_feed.key, str(tvoc))
		aio.send(co_feed.key, str(co))
		aio.send(co2_feed.key, str(co2))
	except: #TODO send text if aio_error_sent is false, set true after
		print("Error posting to AIO. Not parsing error. Probably trying "
						"again in a few seconds...")
		sendAlert("Air Quality Alert:\nFailed to post to AIO.")
	else:
		print('success')

################################################################################
app.run()

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
					if end_index != -1:
						data = data[:end_index]
						parseAndPost(data)
						#print('Received: %s' % data)
						data = ''
						found_begin = False
		
	except IOError:
		pass
	
	except KeyboardInterrupt:
		print('\nClosing connection...')
		socket.close()
		print('Done.')
		break
