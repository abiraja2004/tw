var deb_var=null;
var deb_var2=null;

$(function () {   
    $('#tweet-box').slimScroll({
        height: '705px'
    });
        
    tweets_count_group_by = "day";
    $(".tweet_count_group_by").click(function (e) { 
        tweets_count_group_by = $(this).attr('group_by') 
    fetchTweetsCount([[updateTweetCountLineChart, ['brand']],
                     [updateTweetCountLineChart, ['product']], 
                     [updateTweetCountPieChart, ['sentiment', {'+': ['pos', 'green'], '-': ['neg','red'], '=': ['neu','yellow'], '?': ['irr', 'gray']}]], 
                     [updateIndicators]]);

    });
    
});

function dateRangeChanged()
{
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    
    fetchTweets(account_id, campaign_id, true);
    
    fetchTweetsCount([[updateTweetCountLineChart, ['brand']],
                     [updateTweetCountLineChart, ['product']], 
                     [updateTweetCountPieChart, ['sentiment', {'+': ['pos', 'green'], '-': ['neg','red'], '=': ['neu','yellow'], '?': ['irr', 'gray']}]], 
                     [updateIndicators]]);
    fetchAnalyticsSessions();
}

function updateIndicators(data)
{
    $('#total_tweets').html(''+data['stats']['total_tweets']);
    $('#own_tweets').html(''+data['stats']['own_tweets']['total']);
    $('#mentions_indicator').html(''+data['stats']['mentions']['total']);
    $('#reweets').html(''+data['stats']['own_tweets']['retweets']['total']);
    $('#favorites').html(''+data['stats']['own_tweets']['favorites']['total']);
}

function fetchAnalyticsSessions()
{
    data = {}
    data['campaign_id'] = $('[fn=c_id]').val();;
    data['account_id'] = $('[fn=a_id]').val();
    
    startend = getDateRange();
    data['start'] = startend[0].format("YYYY-MM-DD");
    data['end'] = startend[1].format("YYYY-MM-DD");
    
    $.ajax({
        url: "/api/account/analytics/sessions", 
        contentType: 'application/json',
        dataType: 'json',
        data: data, 
        type: "GET",
        processData: true,
    }).done(function (response) {
        if (response['error'] != '')
        {
            $('#analytics_sessions').html(response['error']);
        }
        else
        {
            $('#analytics_sessions').html(response['res']);
        }
    });   
}
