var clientId = '442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com';
var apiKey = 'AIzaSyDa2z27CHqaqLDSR2X7OZwbBwmgIyNtT7g';
var scopes = 'https://www.googleapis.com/auth/analytics.readonly';

// This function is called after the Client Library has finished loading
function handleClientLoad() {
  gapi.client.setApiKey(apiKey);
  window.setTimeout(checkAuth,1);
}


function checkAuth() {
  gapi.auth.authorize({client_id: clientId, scope: scopes, immediate: true}, handleAuthResult);
}


function handleAuthResult(authResult) {
    if (authResult && !authResult.error) { //Add check for error!!
    // The user has authorized access
    // Load the Analytics Client. This function is defined in the next section.
    loadAnalyticsClient();
  } else {
    // User has not Authenticated and Authorized
    handleUnAuthorized();
  }
}


// Authorized user
function handleAuthorized() {
  var authorizeButton = document.getElementById('authorize-button');
  var makeApiCallButton = document.getElementById('make-api-call-button');

  makeApiCallButton.style.visibility = '';
  authorizeButton.style.visibility = 'hidden';
  makeApiCallButton.onclick = makeApiCall;
}


// Unauthorized user
function handleUnAuthorized() {
  var authorizeButton = document.getElementById('authorize-button');
  var makeApiCallButton = document.getElementById('make-api-call-button');

  makeApiCallButton.style.visibility = 'hidden';
  authorizeButton.style.visibility = '';
  authorizeButton.onclick = handleAuthClick;
}


function handleAuthClick(event) {
  gapi.auth.authorize({client_id: clientId, scope: scopes, immediate: false}, handleAuthResult);
  return false;
}


function loadAnalyticsClient() {
  // Load the Analytics client and set handleAuthorized as the callback function
  gapi.client.load('analytics', 'v3', handleAuthorized);
}