#!/usr/bin/python3
from Adafruit_IO import Client, Feed
from flask import Flask, Response, request
from twilio.twiml.messaging_response import Message, MessagingResponse
from twilio.rest import Client as TwilioClient
from datetime import datetime
import logging
# On recieving a text, this pulls data from AIO and returns to sender
logging.basicConfig(filename='src/aq_sms_responder.log',level=logging.INFO,
                    format = '%(asctime)s %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
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

def translateToFeedname(feed):
	feedname = None
	if feed == 'temp':
		feedname = 'arduino-air-quality-monitor.temperature'
	elif feed == 'hum':
		feedname = 'arduino-air-quality-monitor.humidity'
	elif feed == 'pm10':
		feedname = 'arduino-air-quality-monitor.pm10'
	elif feed == 'pm25':
		feedname = 'arduino-air-quality-monitor.pm25'
	elif feed == 'tvoc':
		feedname = 'arduino-air-quality-monitor.tvoc'
	elif feed == 'co':
		feedname = 'arduino-air-quality-monitor.co'
	elif feed == 'co2':
		feedname = 'arduino-air-quality-monitor.co2'
	else:
		feedname = -1
	return feedname


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
	feed = translateToFeedname(feedname)
	if feed != -1:
		retval = aio.receive(feed).value
	else:
		retval = f'Could not retrieve {feedname} from AIO...'
	return retval

def getEntireFeed(feedname):
	feed = translateToFeedname(feedname)
	if feed != -1:
		data = aio.data(feed)
	else:
		data = -1
	total = 0
	count = 0
	for stuff in data:
		total += float(stuff.value)
		count += 1
	return total/count

def getSomeFeed(feedname, weeks):
	feed = translateToFeedname(feedname)
	# week
	if weeks == 1:
		div = 4
	# 2 weeks
	elif weeks == 2:
		div = 2
	# 3 weeks
	elif weeks == 3:
		div = (4/3)
	# month
	elif weeks == 4:
		div = 1
	# day
	elif weeks == 24:
		div = 30
	else:
		div = 10000
	if feed != -1:
		data = aio.data(feed)
	else:
		data = -1
	total = 0
	count = 0
	data_count = (len(data)/div)
	for stuff in data:
		if count == data_count:
			return total/count
		total += float(stuff.value)
		count += 1
	return total/count


###############################################################################
app = Flask(__name__)

@app.route('/sms', methods=['GET','POST']) # url/sms 
def sms():
	number = request.form['From']
	msg_body = request.form['Body']
	new_request = msg_body.lower().strip()
	logging.info(f'New Request: {new_request}')
	# Only respond to my number
	if number != my_num:
		msg = 'Warning: Unknown number.'
		return
	else: # response based on incoming request
		resp = MessagingResponse() # create msg to be returned
		if new_request == 'commands':
			msg = ('AQ Commands:\n\n-all: current feed values\n\n-temp/hum etc: specific value\n'
			'\n-month + feed: month average\n\n-week + feed: week average\n'
			'\n-2 week + feed: 2 week feed average\n\n-day + feed: day average\n'
			'\n-avg + feed: all feed averages\n'
			'\n-feeds: list available feeds')
		elif new_request == 'feeds':
			all_feeds = 'Available Feeds:\n\n'
			for feed in feeds:
				all_feeds += f'-{feed}\n'
			msg = all_feeds
		elif new_request == 'all':
			msg = getAllFeedsCurrent()
		elif new_request.startswith('month'):
			rqst = new_request[6:] # remove month to find feed
			#logging.info(f'Request after strip: {rqst}')
			if rqst in feeds:
				msg = str(round(getSomeFeed(rqst, 4), 2))
				#logging.info(f'getSomeFeed() returned: {msg}')
			else:
				msg = f'Couldnt find feed: {rqst}'
		elif new_request.startswith('week'):
			rqst = new_request[5:]
			msg = str(round(getSomeFeed(rqst, 1), 2))
		elif new_request.startswith('2 week'):
			rqst = new_request[7:]
			msg = str(round(getSomeFeed(rqst, 2), 2))
		elif new_request.startswith('day'):
			rqst = new_request[4:]
			msg = str(round(getSomeFeed(rqst, 24), 2))
		elif new_request.startswith('avg'):
			rqst = new_request[4:]
			day_avg = str(round(getSomeFeed(rqst, 24), 2))
			week_avg = str(round(getSomeFeed(rqst, 1), 2))
			two_week_avg = str(round(getSomeFeed(rqst, 2), 2))
			month_avg = str(round(getSomeFeed(rqst, 4), 2))
			msg = f'{rqst} averages:\n\nDay: {day_avg}\nWeek: {week_avg}\n2 Week: {two_week_avg}\nMonth: {month_avg}'
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
