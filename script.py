from pymongo import MongoClient
from brandclassifier import BrandClassifier
from datetime import datetime
import re
local = MongoClient()
remoto = MongoClient("prodedelmundial.com.ar")
monitor_local = local['monitor']
monitor_remoto = remoto['monitor']
monitor_remoto.authenticate("monitor", "monitor678")

doc = monitor_local.accounts.find_one({"name": "General Motors"})
print monitor_remoto.accounts.save(doc)
