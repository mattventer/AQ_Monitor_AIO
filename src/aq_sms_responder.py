#!/usr/bin/python3
from Adafruit_IO import Client, Feed
from flask import Flask, Response, request
from twilio.twiml.messaging_response import Message, MessagingResponse
from twilio.rest import Client as TwilioClient
from datetime import datetime
import logging
# On recieving a text, this pulls data from AIO and returns to sender
logging.basicConfig(filename='src/aq_sms_responder.log',level=logging.INFO)
twilio_num = None
my_num = None
TWIL_SID = None
TWIL_TOKEN = None
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
feeds = ['temp','hum','pm10','pm25','tvoc','co','co2']
try:
	with open(key_file) as f:
		content = f.readlines()
		content = [x.strip() for x in content]
		f.close()
except:
		logging.error("Could not load info from keys.txt.")
		exit()
else:
		if len(content) == 6:
			twilio_num = content[0]
			my_num = content[1]
			TWIL_SID = content[2]
			TWIL_TOKEN = content[3]
			ADAFRUIT_IO_USERNAME = content[4]
			ADAFRUIT_IO_KEY = content[5]
		else:
			logging.error('Error: Could not get keys from keys.txt')
			exit()
		# Only runs after loading keys successfully
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

###############################################################################
# Functions to be used within sms()
# returns a list of current feed values
def getAllFeedsCurrent():
	retdata = []
	response = 'Current values:\n'
	retdata.append(aio.receive('arduino-air-quality-monitor.temperature').value)
	retdata.append(aio.receive('arduino-air-quality-monitor.humidity').value)
	retdata.append(aio.receive('arduino-air-quality-monitor.pm10').value)
	retdata.append(aio.receive('arduino-air-quality-monitor.pm25').value)
	retdata.append(aio.receive('arduino-air-quality-monitor.tvoc').value)
	retdata.append(aio.receive('arduino-air-quality-monitor.co').value)
	retdata.append(aio.receive('arduino-air-quality-monitor.co2').value)
	count = 0
	for data in retdata:
		response += (f'{feeds[count]}: {data}\n')
		count += 1
	return response

def getSpecificFeedCurrent(feedname):
	retval = None
	if feedname == 'temp':
		retval = aio.receive('arduino-air-quality-monitor.temperature').value
	elif feedname == 'hum':
		retval = aio.receive('arduino-air-quality-monitor.humidity').value
	elif feedname == 'pm10':
		retval = aio.receive('arduino-air-quality-monitor.pm10').value
	elif feedname == 'pm25':
		retval = aio.receive('arduino-air-quality-monitor.pm25').value
	elif feedname == 'tvoc':
		retval = aio.receive('arduino-air-quality-monitor.tvoc').value
	elif feedname == 'co':
		retval = aio.receive('arduino-air-quality-monitor.co').value
	elif feedname == 'co2':
		retval = aio.receive('arduino-air-quality-monitor.co2').value
	else:
		retval = f'Could not retrieve {feedname} from AIO...'
	return retval


###############################################################################
app = Flask(__name__)

@app.route('/sms', methods=['GET','POST']) # url/sms 
def sms():
	logging.info('Recieved new sms')
	number = request.form['From']
	msg_body = request.form['Body']
	new_request = msg_body.lower().strip()
	# Only respond to my number
	if number != my_num:
		msg = 'Warning: Unknown number.'
		return
	else: # response based on incoming request
		resp = MessagingResponse() # create msg to be returned
		if new_request == 'commands':
			msg = 'AQ Commands\n-all: current feed values\n-temp/hum etc: specific value'
		elif new_request == 'all':
			msg = getAllFeedsCurrent()
		elif new_request in feeds:
			#return
			msg = getSpecificFeedCurrent(new_request)
		else:
			msg = 'Unknown command. Type commands.'
	
	resp.message(msg)
	return str(resp)


# Run the app
if __name__ == '__main__':
	logging.info('Starting sms server')
	app.run(debug=True)
