from pymongo import MongoClient

dbuser = "monitor"
dbpasswd = "monitor678"
remote = MongoClient("nuev9.com")['monitor']
remote.authenticate(dbuser, dbpasswd)
local = MongoClient()['monitor']


laccs = set([x['_id'] for x in local.accounts.find()])
accs = remote.accounts.find({})


for acc in accs:
    if acc['_id'] not in laccs:
        local.accounts.save(acc)