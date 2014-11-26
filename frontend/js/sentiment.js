var deb_var=null;
var deb_var2=null;

$(function () {   
    $('#tweet-box').slimScroll({
        height: '500px'
    });
        
    tweets_count_group_by = "day";
    $(".tweet_count_group_by").click(function (e) { 
        tweets_count_group_by = $(this).attr('group_by') 
        //fetchTweetsCount('sentiment', {labelsFunction: chartLabels,colorsFunction: chartColors})
        fetchTweetsCount([[updateTweetCountLineChart, ['sentiment', {labelsFunction: chartLabels,colorsFunction: chartColors}]]]);
    });
});

function dateRangeChanged()
{
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    //brands_to_include = $('#brands_to_include').val();
    fetchTweets(account_id, campaign_id, false);
    fetchTweetsCount([[updateTweetCountLineChart, ['sentiment', {labelsFunction: chartLabels,colorsFunction: chartColors}]]]);
    //fetchTweetsCount('sentiment', {labelsFunction: chartLabels,colorsFunction: chartColors})
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

function chartLabels(dimensions)
{
    map = {'+': 'pos', '-': 'neg', '=': 'neu', '?': 'irr'}
    for (i=0;i<dimensions.length; i++) dimensions[i] = map[dimensions[i]]
    return dimensions;
}

function chartColors(dimensions)
{
    map = {'+': 'green', '-': 'red', '=': 'yellow', '?': 'gray'}
    for (i=0;i<dimensions.length; i++) dimensions[i] = map[dimensions[i]]
    return dimensions;
}