import pymongo

from gnip.mongo import MongoManager
from pprint import pprint

MongoManager.connect()

accs = MongoManager.getActiveAccounts()
for acc in accs:
    for cmp in acc.getActiveCampaigns():
        print cmp.getName() + ": ",cmp.o['active']
        cmp.o['active'] = False
        MongoManager.saveCampaign(acc, cmp)
