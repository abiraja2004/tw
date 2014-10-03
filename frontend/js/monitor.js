var deb_var3 = null;
tweets_count_group_by = 'day';
brands_to_include = '';

function getDateRange()
{
    return [$('#daterange').daterangepicker().data().daterangepicker.startDate, $('#daterange').daterangepicker().data().daterangepicker.endDate];
    
}

function getNewId(func)
{
 $.ajax({
        url: "/api/objectid/new", 
        data: {}, 
        type: "GET",
    }).done(function (new_id) {
        func(new_id)
    });
}


function fetchTweets(account_id, campaign_id, include_sentiment_tagged_tweets)
{   
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");

    $.ajax({
        url: "/api/tweets/list", 
        data: {"account_id": account_id, 'campaign_id': campaign_id, 'start': start, 'end': end, 'include_sentiment_tagged_tweets': include_sentiment_tagged_tweets, 'brands_to_include': brands_to_include}, 
        type: "GET",
    }).done(function (response) { 
        updateTweetBox(response)
    });
}


function updateTweetBox(response)
{
    tweets = response['tweets'];
    //mentions = 0;
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
        //if ('x_mentions_count' in tweet)
        //{
        //    for (m in tweet['x_mentions_count']) mentions = mentions + tweet['x_mentions_count'][m];
        //}
        if ('x_extracted_info' in tweet && tweet['x_extracted_info'].length > 0)
        {
                brand = tweet['x_extracted_info'][0]['brand'];
                product = tweet['x_extracted_info'][0]['product'];
                confidence = tweet['x_extracted_info'][0]['confidence'];
        }
        topicshtml = "";
        br = "<br>";
        if ('x_extracted_topics' in tweet && tweet['x_extracted_topics'].length > 0)
        {
            for (var j=0;j<tweet['x_extracted_topics'].length; j++)
            {
                topic = tweet['x_extracted_topics'][j];
                topicshtml = topicshtml + br + '<small class="badge pull-left bg-aqua">'+topic['topic_name'] + ' (' + topic['confidence'] + ')</small> ';
                br = "";
            }
        }
        tweettag = $(html.replace("%%_id%%", tweet['_id']['$oid'])
                    .replace("%%created_at%%", tweet['created_at'])
                    .replace("%%user.screen_name%%", tweet['user']['screen_name'])
                    .replace("%%text%%", tweet['text'])
                    .replace("%%sentiment%%", sent)
                    .replace("%%sentiment_color%%", color)
                    .replace("%%brand%%", brand)
                    .replace("%%product%%", product)
                    .replace("%%confidence%%", confidence)
                    .replace("%%user.profile_image_url_https%%", "src='"+tweet['user']['profile_image_url_https']+"'")                    
                    .replace("%%topics%%", topicshtml)
                    );    
        
        tweetbox.append(tweettag);
    }
    //$('#mentions_indicator').html(''+mentions);
}


function fetchTweetsCount(callbacks)
{
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    $.ajax({
        url: "/api/tweets/count", 
        data: {'start': start, 'end': end, 'group_by': tweets_count_group_by, "account_id": account_id, 'campaign_id': campaign_id, brands_to_include: brands_to_include}, 
        type: "GET",
    }).done(function (data) { 
        for (var i=0; i<callbacks.length;i++)
        {
            cb = callbacks[i];
            if (cb.length == 1)
            {
                cb[0](data);
            }
            else
            {
                cb[0](data, cb[1])
            }
        }
    });
}


function updateTweetCountLineChart(data, args)
{
    dimension = args[0];
    options = args[1];
    $('#'+dimension+'-chart').off();
    $('#'+dimension+'-chart').empty();
    if ($.isEmptyObject(data[dimension])) return;
    series = [];
    for (var i = 0;i<data['timerange'].length; i++)
    {
        range = data['timerange'][i];
        item = {};
        item['y'] = range;
        for (dim in data[dimension])
        {
            item[dim] = data[dimension][dim][range]
        }
        series.push(item);
    }
    dims = []
    deb_var = series;
    for (dim in data[dimension]) dims.push(dim)
    chartOptions = {
        element: dimension+'-chart',
        resize: true,
        data: series,
        xkey: 'y',
        hideHover: 'true',
    }
    labels = dims.slice(); //deep copy
    if (options != null)
    {
        if ('labelsFunction' in options) labels = options['labelsFunction'](dims.slice());
        if ('colorsFunction' in options) chartOptions['lineColors'] = options['colorsFunction'](dims.slice());
    }
    chartOptions['ykeys'] = dims;
    chartOptions['labels'] = labels;
    // LINE CHART
    var line = new Morris.Line(chartOptions);   
}

function updateTweetCountPieChart(data, args)
{
    deb_var2 = data;
    dimension = args[0];
    options = args[1];   
    
    d = []
    colors = []
    if (options == null)
    {
        for (dim in data[dimension]) d.push({'label': dim, 'value': data[dimension][dim]['total']})
    }
    else
    {
        for (dim in data[dimension]) 
        {
            d.push({'label': options[dim][0], 'value': data[dimension][dim]['total']});
            colors.push(options[dim][1]);
        }
    }
    
    deb_var2 = d;
    
    var donut = new Morris.Donut({
        element: dimension+'-chart',
        resize: true,
        colors: colors,
        data: d,
        hideHover: 'auto'
    });    
}


function removeComponent(tag)
{
    $(tag).closest(".removible_component").remove();
}

function removeComponentExceptLast(tag)
{
    if (!$(tag).closest(".removible_component").is(":last-child"))
    {
        $(tag).closest(".removible_component").remove();
    }
}