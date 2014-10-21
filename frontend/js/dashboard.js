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
    
    $(".brands_to_include").click(function (e) { 
        brands_to_include = $(this).attr('brands_to_include') 
    fetchTweets(account_id, campaign_id, true);
    fetchFBPosts(account_id, campaign_id);
    updateAggregatedInformation();
    });    
    
});

function dateRangeChanged()
{
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    
    fetchTweets(account_id, campaign_id, true);
    fetchFBPosts(account_id, campaign_id);
    updateAggregatedInformation();
    fetchAnalyticsSessions();
}

function updateAggregatedInformation()
{
    $(".indicator").addClass("loading");
    params = [];
    params.push([updateTweetCountLineChart, ['brand']]);
    params.push([updateTweetCountLineChart, ['product']]);
    params.push([updateTweetCountPieChart, ['sentiment', {'+': ['pos', 'green'], '-': ['neg','red'], '=': ['neu','yellow'], '?': ['irr', 'gray']}]]);
    params.push([updateIndicators]);
    params.push([updatePollsPieCharts, ['polls']]);
    params.push([updateDataCollectionPieCharts, ['datacollections']]);
    fetchTweetsCount(params);
}

function updatePollsPieCharts(data)
{
    $('.poll-chart').remove();
    for (var poll_id in data['polls'])
    {
        poll = data['polls'][poll_id];
        var modeldiv = $('#poll-charts-container').children().first();
        var newdiv = modeldiv.clone()
        newdiv.css("display", "block");
        newdiv.attr("id", poll_id+ "-chart");
        newdiv.addClass("poll-chart")
        modeldiv.parent().append(newdiv);
        updateTweetCountPieChart(poll, poll['data'], [poll_id]);        
    }
}

function updateDataCollectionPieCharts(data)
{
    $('.datacollection-chart').remove();
    for (var datacollection_id in data['datacollections'])
    {
        datacollection = data['datacollections'][datacollection_id];
        var modeldiv = $('#datacollection-charts-container').children().first();
        for (var field in datacollection['data'])
        {
            if ($.isEmptyObject(datacollection['data'][field])) continue;  //algunos campos vienen sin datos xq no son de tipo combobox
            var newdiv = modeldiv.clone()
            newdiv.css("display", "block");
            newdiv.attr("id", datacollection_id+field+ "-chart");
            newdiv.addClass("datacollection-chart")
            modeldiv.parent().append(newdiv);
            updateTweetCountPieChart(datacollection['data'], datacollection['data'][field], [datacollection_id+field]);        
        }
    }
}

function updateIndicators(data)
{
    $('#total_tweets').html(''+data['stats']['total_tweets']);
    $('#own_tweets').html(''+data['stats']['own_tweets']['total']);
    $('#mentions_indicator').html(''+data['stats']['mentions']['total']);
    $('#reweets').html(''+data['stats']['own_tweets']['retweets']['total']);
    $('#favorites').html(''+data['stats']['own_tweets']['favorites']['total']);
    $(".indicator").removeClass("loading");
}

function fetchAnalyticsSessions()
{
    $(".analytics_indicator").addClass("loading");
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
        $(".analytics_indicator").removeClass("loading");
    });   
}
