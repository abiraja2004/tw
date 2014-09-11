tweets_count_group_by = 'day';

function getDateRange()
{
    return [$('#daterange').daterangepicker().data().daterangepicker.startDate, $('#daterange').daterangepicker().data().daterangepicker.endDate];
    
}

function fetchTweets(account_id, campaign_id, include_sentiment_tagged_tweets)
{   
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");

    $.ajax({
        url: "/api/tweets/list", 
        data: {"account_id": account_id, 'campaign_id': campaign_id, 'start': start, 'end': end, 'include_sentiment_tagged_tweets': include_sentiment_tagged_tweets}, 
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
    colors = {'+': 'green', '-':'red', '=':'yellow', '?': 'gray'}
    for (var i=0;i<tweets.length;i++)
    {
        tweet = tweets[i];
        sent = '';
        color= 'white';
        if ('x_sentiment' in tweet) 
        {
            sent = sents[tweet['x_sentiment']];
            color = colors[tweet['x_sentiment']];
        }
        brand = '';
        product = '';
        confidence = '';
        if ('x_extracted_info' in tweet && tweet['x_extracted_info'].length > 0)
        {
                brand = tweet['x_extracted_info'][0]['brand'];
                product = tweet['x_extracted_info'][0]['product'];
                confidence = tweet['x_extracted_info'][0]['confidence'];
        }
        tweettag = $(html.replace("%%_id%%", tweet['_id']['$oid']).replace("%%user.profile_image_url_https%%", tweet['user']['profile_image_url_https'])
                    .replace("%%created_at%%", tweet['created_at'])
                    .replace("%%user.screen_name%%", tweet['user']['screen_name'])
                    .replace("%%text%%", tweet['text'])
                    .replace("%%sentiment%%", sent)
                    .replace("%%sentiment_color%%", color)
                    .replace("%%brand%%", brand)
                    .replace("%%product%%", product)
                    .replace("%%confidence%%", confidence)
                    );    
        tweetbox.append(tweettag);
    }
    
}


function fetchTweetsCount(dimension, options)
{
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    $.ajax({
        url: "/api/tweets/count", 
        data: {'start': start, 'end': end, 'group_by': tweets_count_group_by, 'group_dimension': dimension, "account_id": account_id, 'campaign_id': campaign_id}, 
        type: "GET",
    }).done(function (data) { 
        updateTweetCountLineChart(data, options)
    });
}


function updateTweetCountLineChart(data, options)
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
        for (dimension in data['dimensions'])
        {
            item[dimension] = data['dimensions'][dimension][range]
        }
        series.push(item);
    }
    dimensions = []
    deb_var = series;
    for (dimension in data['dimensions']) dimensions.push(dimension)
    chartOptions = {
        element: 'line-chart',
        resize: true,
        data: series,
        xkey: 'y',
        hideHover: 'true',
    }
    labels = dimensions.slice(); //deep copy
    if (options != null)
    {
        if ('labelsFunction' in options) labels = options['labelsFunction'](dimensions.slice());
        if ('colorsFunction' in options) chartOptions['lineColors'] = options['colorsFunction'](dimensions.slice());
    }
    chartOptions['ykeys'] = dimensions;
    chartOptions['labels'] = labels;
    // LINE CHART
    var line = new Morris.Line(chartOptions);   
}