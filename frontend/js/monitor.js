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
    tweetbox = $("#tweet-box").addClass("loading");
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
        tweetbox = $("#tweet-box").removeClass("loading");
    }
    //$('#mentions_indicator').html(''+mentions);
}


function fetchTweetsCount(callbacks)
{
    for (var i=0; i<callbacks.length;i++)
    {
        if (callbacks[i].length != 1)
        {
            $('#'+callbacks[i][1][0]+'-chart').addClass("loading");
        }
    }
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
    $('#'+dimension+'-chart').removeClass("loading");
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
    console.debug(chartOptions.element);
    console.debug($('#chartOptions.element'));
    var line = new Morris.Line(chartOptions);   
    console.debug("chart drawn");
    $('#'+dimension+'-chart').removeClass("loading")
}

function updateTweetCountPieChart(data, args)
{
    console.debug(1);
    deb_var2 = data;
    dimension = args[0];
    //if ($.isEmptyObject(data[dimension])) return;
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
    $('#'+dimension+'-chart').removeClass("loading");
    console.debug(2);
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

function fetchFBPosts(account_id, campaign_id)
{   
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");

    $.ajax({
        url: "/api/fb_posts/list", 
        data: {"account_id": account_id, 'campaign_id': campaign_id, 'start': start, 'end': end}, 
        type: "GET",
    }).done(function (response) { 
        updateFBPostsBox(response)
    });
}

function updateFBPostsBox(response)
{
    posts = response['posts'];
    //mentions = 0;
    html = $('#fb_posts_model').html();
    postbox = $("#fb_posts-box");
    postbox.html("");    
    sents = {'+': 'pos', '-':'neg', '=':'neu', '?': 'irr'}
    colors = {'+': 'green', '-':'red', '=':'yellow', '?': 'gray'}
    for (var i=0;i<posts.length;i++)
    {
        post = posts[i];
        sent = '';
        color= 'white';
        if ('x_sentiment' in post) 
        {
            sent = sents[post['x_sentiment']];
            color = colors[post['x_sentiment']];
        }
        brand = '';
        product = '';
        confidence = '';
        //if ('x_mentions_count' in tweet)
        //{
        //    for (m in tweet['x_mentions_count']) mentions = mentions + tweet['x_mentions_count'][m];
        //}
        if ('x_extracted_info' in post && post['x_extracted_info'].length > 0)
        {
                brand = post['x_extracted_info'][0]['brand'];
                product = post['x_extracted_info'][0]['product'];
                confidence = post['x_extracted_info'][0]['confidence'];
        }
        topicshtml = "";
        br = "<br>";
        if ('x_extracted_topics' in post && post['x_extracted_topics'].length > 0)
        {
            for (var j=0;j<post['x_extracted_topics'].length; j++)
            {
                topic = post['x_extracted_topics'][j];
                topicshtml = topicshtml + br + '<small class="badge pull-left bg-aqua">'+topic['topic_name'] + ' (' + topic['confidence'] + ')</small> ';
                br = "";
            }
        }
        posttag = $(html.replace("%%_id%%", post['_id']['$oid'])
                    .replace("%%created_at%%", post['created'])
                    .replace("%%user.screen_name%%", post['author:name'])
                    .replace("%%text%%", post['activity:content'])
                    .replace("%%sentiment%%", sent)
                    .replace("%%sentiment_color%%", color)
                    .replace("%%brand%%", brand)
                    .replace("%%product%%", product)
                    .replace("%%confidence%%", confidence)
                    .replace("%%topics%%", topicshtml)
                    );    
        
        postbox.append(posttag);
    }
    //$('#mentions_indicator').html(''+mentions);
}
