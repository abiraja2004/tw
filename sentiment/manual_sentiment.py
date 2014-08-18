from pymongo import MongoClient
from bson import ObjectId
mongoclient = MongoClient()
db = mongoclient['test']

from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    tweets = db.tweets.find({"x_sentiment": {"$exists": False}}).limit(120)
    #tweets = db.tweets.find({"$and": [{'x_coordinates': {"$exists": True}}, {'x_coordinates': {"$ne": None}}, {'lang': {'$eq': 'es'}}]}).limit(120)
    return render_template('rate_tweets.html', tweets=tweets)

@app.route("/rate", methods=['POST'])
def rate():
    print request.form['id'], request.form['sent']
    print db.tweets.update({"_id": ObjectId(request.form['id'])}, {"$set": {"x_sentiment": request.form['sent']}})
    
    return "OK"
    
if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0")

"""
for t in db.tweets.find({"$and": [{'x_coordinates': {"$exists": True}}, {'x_coordinates': {"$ne": None}}, {'lang': {'$eq': 'es'}}]}):
  print
  print '@' + t['user']['screen_name'] 
  print t['text']
  v = raw_input("Sentiment [Positivo (+)/Negativo (-)/Neutral (=) / Not sure (?) / Quit (q)] Default: q? ").lower()
  if v == "q": exit(0)
  elif v == "+": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": "+"}})
  elif v == "-": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": "-"}})
  elif v == "=": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": "="}})
  elif v == "=": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": null}})
"""