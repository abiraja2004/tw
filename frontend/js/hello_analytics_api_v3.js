var deb_var = null;
var deb_var2 = null;
// Execute this function when the 'Make API Call' button is clicked
function makeApiCall() {
  console.log('Starting Request Process...');
  queryAccounts();
}


function queryAccounts() {
  console.log('Querying Accounts.');

  // Get a list of all Google Analytics accounts for this user
  gapi.client.analytics.management.accounts.list().execute(handleAccounts);
}


function handleAccounts(results) {
  if (!results.code) {
    if (results && results.items && results.items.length) {

      account = results.items[0]
      // Get the first Google Analytics account
      var firstAccountId = account.id;
      console.log("accounts: " + results.items.length);
      deb_var = account;
      // Query for Web Properties
      queryWebproperties(firstAccountId);

    } else {
      console.log('No accounts found for this user.')
    }
  } else {
    console.log('There was an error querying accounts: ' + results.message);
  }
}


function queryWebproperties(accountId) {
  console.log('Querying Webproperties.');

  // Get a list of all the Web Properties for the account
  gapi.client.analytics.management.webproperties.list({'accountId': accountId}).execute(handleWebproperties);
}


function handleWebproperties(results) {
  if (!results.code) {
    if (results && results.items && results.items.length) {

      // Get the first Google Analytics account
      var webprop = results.items[0];
      var firstAccountId = webprop.accountId;
      
      console.log("wp:acc:length " + results.items.length);
      deb_var2 = webprop;
      // Get the first Web Property ID
      var firstWebpropertyId = webprop.id;

      // Query for Views (Profiles)
      queryProfiles(firstAccountId, firstWebpropertyId);

    } else {
      console.log('No webproperties found for this user.');
    }
  } else {
    console.log('There was an error querying webproperties: ' + results.message);
  }
}


function queryProfiles(accountId, webpropertyId) {
  console.log('Querying Views (Profiles).');
    console.log(accountId);
  // Get a list of all Views (Profiles) for the first Web Property of the first Account
  gapi.client.analytics.management.profiles.list({
      'accountId': accountId,
      'webPropertyId': webpropertyId
  }).execute(handleProfiles);
}


function handleProfiles(results) {
  if (!results.code) {
    if (results && results.items && results.items.length) {

      // Get the first View (Profile) ID
      var firstProfileId = results.items[0].id;
      console.log(firstProfileId);
      // Query the Core Reporting API
      queryCoreReportingApi(firstProfileId);

    } else {
      console.log('No views (profiles) found for this user.');
    }
  } else {
    console.log('There was an error querying views (profiles): ' + results.message);
  }
}


function queryCoreReportingApi(profileId) {
  console.log('Querying Core Reporting API.');

  // Use the Analytics Service Object to query the Core Reporting API
  gapi.client.analytics.data.ga.get({
    'ids': 'ga:' + profileId,
    'start-date': '2011-07-01',
    'end-date': '2014-09-30',
    'metrics': 'ga:sessions'
  }).execute(handleCoreReportingResults);
}


function handleCoreReportingResults(results) {
  if (results.error) {
    console.log('There was an error querying core reporting API: ' + results.message);

  } else {
    printResults(results);
  }
}


function printResults(results) {
  if (results.rows && results.rows.length) {
    console.log('View (Profile) Name: ', results.profileInfo.profileName);
    deb_var = results;
    console.log('Total Sessions: ', results.rows[0][0]);
  } else {
    console.log('No results found');
  }
}