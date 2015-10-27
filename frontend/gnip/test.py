from pprint import pprint
from pymongo import MongoClient
from bson import ObjectId

dbuser = "monitor"
dbpasswd = "monitor678"
remote = MongoClient("nuev9.com")['monitor']
remote.authenticate(dbuser, dbpasswd)
local = MongoClient()['monitor']

"""
laccs = set([x['_id'] for x in local.accounts.find()])
accs = remote.accounts.find({"_id": ObjectId("54f4b34941b84c23d147babd")})
#pprint(accs[0])

for acc in accs:
    #if acc['_id'] not in laccs:
    local.accounts.save(acc)
"""

acc = remote.accounts.find_one({"_id": ObjectId("54f4b34941b84c23d147babd")})
#pprint (acc)
#acc['campaigns'] = {"iae1": acc['campaigns']['54f4b32141b84c23d147babc']}
#acc['name'] = "INSIGHT-DRINKS-IAE-GRUPO-1"
#acc['users'] = {'iae1': {u'access': u'admin', u'password': u'', u'username': u'iae1'}}
campaign = acc["campaigns"]["54f4b32141b84c23d147babc"]
for x in range(9,10):
    newacc = acc
    newacc["_id"] = ObjectId()
    newacc["campaigns"] = {"iae%s"%x: campaign}
    newacc["name"] = "INSIGHT-DRINKS-IAE-GRUPO-%s" % x
    acc['users'] = {'iae%s'%x: {u'access': u'admin', u'password': u'', u'username': u'iae%s'%x}}
    pprint(newacc["name"])
    pprint(newacc["campaigns"].keys())
    local.accounts.save(newacc)
#pprint(acc)
#pprint (ObjectId())

#local.accounts.save(acc)