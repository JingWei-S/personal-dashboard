from flask import Flask, render_template, request, jsonify, url_for, redirect
from replit import db
import json
import time
from bs4 import BeautifulSoup
import requests


site = Flask(__name__)

def get_price(ticker):
  # use cache if price is not stale
  if ticker in db["shares"].keys() and time.time() < db["shares"][ticker]["last_updated"]+60:
      return db["shares"][ticker]["current_price"]
      
  page = requests.get("https://finance.yahoo.com/quote/" + ticker)
  soup = BeautifulSoup(page.text, "html5lib")
  price = soup.find('fin-streamer', {'class':'Fw(b) Fz(36px) Mb(-4px) D(ib)'}).text

  price = price.replace(",", "")

  # update price in db
  if ticker in db['shares'].keys():
    db['shares'][ticker]['current_price'] = price
    db['shares'][ticker]['last_updated'] = time.time()
  
  return price

@site.route("/")
def index():
  return render_template('index.html')

@site.route("/buy", methods=['post'])
def buy():
  # create shares key if it does not exist in the db
  if 'shares' not in db.keys():
    db['shares'] = {}

  # get ticker
  ticker = request.form['ticker']
  if ticker[0] == "$":
    ticker = ticker[1:]

  ticker = ticker.upper()[:5]

  # get current price
  if not get_price(ticker):
    return f"Ticker $'{ticker}' not found"
  current_price = get_price(ticker)
  
  if not request.form['price']:
    price = float(current_price)
  else:
    price = float(request.form['price'])

  if not request.form['shares']:
    shares = 1
  else:
    shares = int(request.form['shares'])

  if ticker not in db['shares']:
    db['shares'][ticker] = {'total_share': shares,
                             'total_cost': shares * price}
    db['shares'][ticker]['purchases'] = [{ 'shares': shares, 
                                           'price': price}]  # use an array to track
  else:
    db['shares'][ticker]['total_share'] += shares
    db['shares'][ticker]['total_cost'] += shares * price
    db['shares'][ticker]['purchases'].append({ 'shares': shares, 
                                               'price': price})

  db['shares'][ticker]['current_price'] = current_price
  db['shares'][ticker]['last_updated'] = time.time()
  return redirect(url_for("index"))

@site.route('/portfolio')
def portfolio():
  if 'shares' not in db.keys():
    return jsonify({})

  portfolio = json.loads(db.get_raw('shares'))

  # get values
  for ticker in portfolio.keys():
    current_price = float(get_price(ticker))
    current_value = current_price * portfolio[ticker]['total_share']
    portfolio[ticker]['current_value'] = current_value

  return jsonify(**portfolio)   # return a json file of the current portfolio

@site.route('/flush')
def flush_db():
  del db['shares']
  return redirect(url_for("index"))

site.run(host='0.0.0.0', port=8080)