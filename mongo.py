from pymongo import MongoClient
client = MongoClient()
db = client['test']
for d in db.testData.find():
    print d