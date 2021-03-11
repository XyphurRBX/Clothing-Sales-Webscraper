from flask import Flask, request
from flask import jsonify
import datacollection
import threading

app = Flask(__name__)

@app.route('/')
def home():
	return 'This is an API to get user sales through their userid'

@app.route('/getsales/')
def returnSales():
	print('request received')
	userid = request.args.get('userid', type = str)
	sales = datacollection.GetTotalSales(userid)
	return {userid : sales}

if __name__ == 'main':
	app.run(threaded = True)