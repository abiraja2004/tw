var deb_var=null;
var deb_var2=null;

$(function () {   
    $('#tweet-box').slimScroll({
        height: '500px'
    });
        
    tweets_count_group_by = "day";
    $(".tweet_count_group_by").click(function (e) { 
        tweets_count_group_by = $(this).attr('group_by') 
        fetchTweetsCount();
    });
});

function dateRangeChanged()
{
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    
    fetchTweets(account_id, campaign_id);
    fetchTweetsCount()
}

function fetchTweets(account_id, campaign_id)
{   
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");

    $.ajax({
        url: "/api/tweets/list", 
        data: {"account_id": account_id, 'campaign_id': campaign_id, 'start': start, 'end': end}, 
        type: "GET",
    }).done(function (tweets) { 
        updateTweetBox(tweets)
    });
}

function updateTweetBox(tweets)
{
    html = $('#tweet_model').html();
    tweetbox = $("#tweet-box");
    tweetbox.html("");    
    sents = {'+': 'pos', '-':'neg', '=':'neu', '?': 'irr'}
    for (var i=0;i<tweets.length;i++)
    {
        tweet = tweets[i];
        sent = '';
        if ('x_sentiment' in tweet) sent = sents[tweet['x_sentiment']];
        tweettag = $(html.replace("%%_id%%", tweet['_id']['$oid']).replace("%%user.profile_image_url_https%%", tweet['user']['profile_image_url_https'])
                    .replace("%%created_at%%", tweet['created_at'])
                    .replace("%%user.screen_name%%", tweet['user']['screen_name'])
                    .replace("%%text%%", tweet['text']).replace("%%sentiment%%", sent));    
        tweetbox.append(tweettag);
    }
    
}


function tagSentiment(btn, sent)
{
    tweettag = $(btn).closest(".tweet")
    tweet_id = tweettag.attr("tweet_id");
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    $.ajax({
        url: "/api/tweets/tag/sentiment", 
        data: {'tweet_id': tweet_id, 'sentiment': sent, "account_id": account_id, 'campaign_id': campaign_id}, 
        type: "POST",
    }).done(function (data) { 
        tweettag.hide('slow');
    });    
}

function fetchTweetsCount()
{
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    $.ajax({
        url: "/api/tweets/count", 
        data: {'start': start, 'end': end, 'group_by': tweets_count_group_by, "account_id": account_id, 'campaign_id': campaign_id}, 
        type: "GET",
    }).done(function (data) { 
        updateTweetCountLineChart(data)
    });
}


function updateTweetCountLineChart(data)
{
    deb_var2 = data;
    $('#line-chart').off();
    $('#line-chart').empty();
    
    series = [];
    for (var i = 0;i<data['timerange'].length; i++)
    {
        range = data['timerange'][i];
        item = {};
        item['y'] = range;
        for (brand in data['brands'])
        {
            item[brand] = data['brands'][brand][range]
        }
        series.push(item);
    }
    brands = []
    deb_var = series;
    for (brand in data['brands']) brands.push(brand)
    // LINE CHART
    var line = new Morris.Line({
        element: 'line-chart',
        resize: true,
        data: series,
        xkey: 'y',
        ykeys: brands,
        labels: brands,
        hideHover: 'true'
    });   
}