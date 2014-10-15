#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

# import the Auth Helper class

from apiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError


def main(argv):
  # Initialize the Analytics Service Object
  import analytics
  service = analytics.initialize_service()

  try:
    # Query APIs, print results
    profile_id = get_first_profile_id(service)

    if profile_id:
      results = get_results(service, profile_id)
      print_results(results)

  except TypeError, error:
    # Handle errors in constructing a query.
    print ('There was an error in constructing your query : %s' % error)

  except HttpError, error:
    # Handle API errors.
    print ('Arg, there was an API error : %s : %s' %
           (error.resp.status, error._get_reason()))

  except AccessTokenRefreshError:
    # Handle Auth errors.
    print ('The credentials have been revoked or expired, please re-run '
           'the application to re-authorize')


def get_all_profiles(service):
  # Get a list of all Google Analytics accounts for this user
  accounts = service.management().accounts().list().execute()
  res = []
  for account in accounts.get('items'):
    account_id = account.get('id')
    # Get a list of all the Web Properties for the account
    webproperties = service.management().webproperties().list(accountId=account_id).execute()
    if webproperties.get('items'):
        for webproperty in webproperties.get('items'):
            webproperty_id = webproperty.get('id')

            # Get a list of all Views (Profiles) for the Web Property of the Account
            profiles = service.management().profiles().list(accountId=account_id,webPropertyId=webproperty_id).execute()
            res.extend(profiles.get('items'))
  return res

def get_first_profile_id(service):
  # Get a list of all Google Analytics accounts for this user
  accounts = service.management().accounts().list().execute()

  if accounts.get('items'):
    # Get the first Google Analytics account
    firstAccountId = accounts.get('items')[0].get('id')

    # Get a list of all the Web Properties for the first account
    webproperties = service.management().webproperties().list(accountId=firstAccountId).execute()

    if webproperties.get('items'):
      # Get the first Web Property ID
      firstWebpropertyId = webproperties.get('items')[0].get('id')

      # Get a list of all Views (Profiles) for the first Web Property of the first Account
      profiles = service.management().profiles().list(
          accountId=firstAccountId,
          webPropertyId=firstWebpropertyId).execute()

      if profiles.get('items'):
        # return the first View (Profile) ID
        return profiles.get('items')[0].get('id')

  return None


def get_sessions(service, profile_id, start, end):
  # Use the Analytics Service Object to query the Core Reporting API
  return service.data().ga().get(
      ids='ga:' + profile_id,
      start_date=start.strftime("%Y-%m-%d"),
      end_date=end.strftime("%Y-%m-%d"),
      metrics='ga:sessions').execute()


def print_results(results):
  # Print data nicely for the user.
  if results:
    print 'First View (Profile): %s' % results.get('profileInfo').get('profileName')
    print 'Total Sessions: %s' % results.get('rows')[0][0]

  else:
    print 'No results found'


if __name__ == '__main__':
  main(sys.argv)