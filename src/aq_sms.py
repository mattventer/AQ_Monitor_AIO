from flask import Flask, request
from Adafruit_IO import Client, Feed
app = Flask(__name__)

@app.route('/sms', methods=['POST'])
def sms():
	number = request.form['From']
	message_body = request.form['Body']
	resp = twiml.Response()
	resp.message('Hello {}, you said: {}' .format(number, message_body))
	return str(resp)

