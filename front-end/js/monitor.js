
function dateRangeChanged(start, end)
{
    account = '1';
    campaign = '2'
    fetchTweets(start.format("YYYY-MM-DD"), end.format("YYYY-MM-DD"), account, campaign);
    fetchTweetsCount(start.format("YYYY-MM-DD"), end.format("YYYY-MM-DD"))
}

function fetchTweets(start, end, account_id, campaign_id)
{   
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
    html = ''+
    '<div class="item">' +
        '<img src="%%user.profile_image_url_https%%" alt="user image" class="online"/>' +
        '<p class="message">' +
            '<a href="#" class="name">' +
                '<small class="text-muted pull-right"><i class="fa fa-clock-o"></i> %%created_at%%</small>' +
                '%%user.screen_name%%' +
            '</a>' + 
            '%%text%%' +
        '</p>' +
    '</div>';
    tweetbox = $("#tweet-box");
    tweetbox.html("");    
    for (var i=0;i<tweets.length;i++)
    {
        tweet = tweets[i];
        tweettag = $(html.replace("%%user.profile_image_url_https%%", tweet['user']['profile_image_url_https'])
                    .replace("%%created_at%%", tweet['created_at'])
                    .replace("%%user.screen_name%%", tweet['user']['screen_name'])
                    .replace("%%text%%", tweet['text']))
        tweetbox.append(tweettag);
    }
    
}

function fetchTweetsCount(start, end)
{
        $.ajax({
        url: "/api/tweets/count", 
        data: {'start': start, 'end': end}, 
        type: "GET",
    }).done(function (data) { 
        updateTweetCountLineChart(data)
    });
}


function updateTweetCountLineChart(data)
{
    $('#line-chart').off();
    $('#line-chart').empty();
    
    series = [];
    for (var i = 0;i<data['timerange'].length; i++)
    {
        range = data['timerange'][i];
        for (brand in data['brands'])
        {
            item = {};
            item['y'] = range;
            item[brand] = data['brands'][brand][range]
            series.push(item);
        }
    }
    brands = []
    for (brand in data['brands']) brands.push(brand)
    // LINE CHART
    var line = new Morris.Line({
        element: 'line-chart',
        resize: true,
        data: series,
        xkey: 'y',
        ykeys: brands,
        labels: brands,
        hideHover: 'auto'
    });
    
}