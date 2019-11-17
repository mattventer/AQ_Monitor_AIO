from Adafruit_IO import Client, Feed
from flask import Flask, Response, request
from twilio import twiml
from datetime import datetime
import logging
# On recieving a text, this pulls data from AIO and returns to sender
logging.basicConfig(filename='aq_sms_responder.log',level=logging.INFO)

app = Flask(__name__)

@app.route('/sms', methods=['GET','POST']) # url/sms 
def sms():
	logging.info('Recieved new sms')
	number = request.form['From']
	msg_body = request.form['Body']
	resp = twiml.Response() # create msg to be returned
	resp.message('Hello {}, you said: {}'.format(number, msg_body))
	return str(resp)


# Run the app
if __name__ == '__main__':
	logging.info('Starting sms server')
	app.run(debug=True)