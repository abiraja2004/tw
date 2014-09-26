#!/usr/bin/python

import httplib2

from apiclient.discovery import build

from oauth2client.client import flow_from_clientsecrets, OAuth2WebServerFlow
from oauth2client.file import Storage
from oauth2client.tools import run

CLIENT_SECRETS = 'client_secrets.json'
MISSING_CLIENT_SECRETS_MESSAGE = '%s is missing' % CLIENT_SECRETS

FLOW = OAuth2WebServerFlow(client_id='442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com',
                           client_secret='43Bf_67s6E9PXIJe4ZY5fUSC',
                           scope='https://www.googleapis.com/auth/analytics.readonly',
                           redirect_uri='http://localhost:5001/oauth2callback')
"""
FLOW = flow_from_clientsecrets(CLIENT_SECRETS,
  scope='https://www.googleapis.com/auth/analytics.readonly',
  message=MISSING_CLIENT_SECRETS_MESSAGE)
"""
print FLOW.client_id,FLOW.redirect_uri, "ACA"
TOKEN_FILE_NAME = 'analytics.dat'

def prepare_credentials():
  storage = Storage(TOKEN_FILE_NAME)
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    print "INVALID CREDENTIALS"
    print dir(FLOW)
    print FLOW.step1_get_authorize_url()
    credentials = run(FLOW, storage)
  return credentials

def initialize_service():
  http = httplib2.Http()

  #Get stored credentials or run the Auth Flow if none are found
  print 1
  credentials = prepare_credentials()
  print 2
  http = credentials.authorize(http)
  print 3
  #Construct and return the authorized Analytics Service Object
  return build('analytics', 'v3', http=http)