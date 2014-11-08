brands_to_include = '';

$(function () {   

    $(".brands_to_include").click(function (e) { 
        brands_to_include = $(this).attr('brands_to_include') ;
        search();
    });    
    
});



function dateRangeChanged()
{
    search();
    //fetchTweetsCount('sentiment', {labelsFunction: chartLabels,colorsFunction: chartColors})
}

function searchTextChanged()
{
    search();
}

function search()
{   
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    tweetbox = $("#feed-box").addClass("loading");
    object_id = $("#object_id").val();
    $("#object_id").val('');
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");
    text = $("#search_text").val();
    $.ajax({
        url: "/api/feeds/search", 
        data: {"account_id": account_id, 
               'campaign_id': campaign_id, 
               'start': start, 
               'end': end, 
               'text': text,
               'brands_to_include': brands_to_include,
               'object_id': object_id
        }, 
        type: "GET",
    }).done(function (response) { 
        updateFeedsContent(response)
    });
}

function updateFeedsContent(response)
{
    feeds = response['feeds'];
    //mentions = 0;
    html = $('#feed_model').html();
    feedbox = $("#feed-box");
    feedbox.html("");    
    sents = {'+': 'pos', '-':'neg', '=':'neu', '?': 'irr'}
    colors = {'+': 'green', '-':'red', '=':'yellow', '?': 'gray'}
    for (var i=0;i<feeds.length;i++)
    {
        feed = feeds[i];
        sent = '';
        color= 'white';
        if ('x_sentiment' in feed) 
        {
            sent = sents[feed['x_sentiment']];
            color = colors[feed['x_sentiment']];
        }
        brand = '';
        product = '';
        confidence = '';
        //if ('x_mentions_count' in tweet)
        //{
        //    for (m in tweet['x_mentions_count']) mentions = mentions + tweet['x_mentions_count'][m];
        //}
        if ('x_extracted_info' in feed && feed['x_extracted_info'].length > 0)
        {
                brand = feed['x_extracted_info'][0]['brand'];
                product = feed['x_extracted_info'][0]['product'];
                confidence = feed['x_extracted_info'][0]['confidence'];
        }
        topicshtml = "";
        br = "<br>";
        if ('x_extracted_topics' in feed && feed['x_extracted_topics'].length > 0)
        {
            for (var j=0;j<feed['x_extracted_topics'].length; j++)
            {
                topic = feed['x_extracted_topics'][j];
                topicshtml = topicshtml + br + '<small class="badge pull-left bg-aqua">'+topic['topic_name'] + ' (' + topic['confidence'] + ')</small> ';
                br = "";
            }
        }
        
        feed_url = "https://www.twitter.com/" + feed['user']['screen_name'] + "/status/" + feed['id_str'];
        user_url = "https://www.twitter.com/" + feed['user']['screen_name'];
        feed_date = new Date(feed['x_created_at']['$date'])
        feedtag = $(html.replace("%%_id%%", feed['_id']['$oid'])
                    .replace("%%created_at%%", feed_date)
                    .replace("%%user.name%%", feed['user']['screen_name'])
                    .replace("%%text%%", feed['text'])
                    .replace("%%sentiment%%", sent)
                    .replace("%%sentiment_color%%", color)
                    .replace("%%brand%%", brand)
                    .replace("%%product%%", product)
                    .replace("%%confidence%%", confidence)
                    .replace("%%user.profile_image_url%%", "src='"+feed['user']['profile_image_url_https']+"'")                    
                    .replace("%%topics%%", topicshtml)
                    .replace("%%feed_url%%", feed_url)
                    .replace("%%user_profile_url%%", user_url)
                    .replace("%%user_profile_url%%", user_url)
                    );    
        
        tweetbox.append(feedtag);
    }
    tweetbox = $("#feed-box").removeClass("loading");
    //$('#mentions_indicator').html(''+mentions);
}

var item;
function removeFeed(btn)
{
    if (!window.confirm("Estás seguro que quieres eliminar el tweet?")) return 
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();    
    item = $(btn).closest(".item");
    feed_object_id = item.find("input[name=id]").val();
    $.ajax({
        url: "/api/feeds/remove", 
        data: {"account_id": account_id, 
               'campaign_id': campaign_id, 
               'feed_object_id': feed_object_id, 
        }, 
        type: "GET",
    }).done(function (response) { 
        if (response['result'] == 'ok')
        {
            item.hide(500);
        }
    });
    
}