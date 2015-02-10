$('input:checkbox').on('ifChanged', function () {
    search();
});
//$('input#source_twitter,input#source_facebook,input#source_forums')

function dateRangeChanged()
{
    monitor_dateRangeChanged();
    search();
    //fetchTweetsCount('sentiment', {labelsFunction: chartLabels,colorsFunction: chartColors})
}

function searchTextChanged()
{
    search();
}

function filterBrandChanged()
{
    selected_brands = $("#filter_brand").val().split("|");
    var options = '';
    options = '<option value="" selected >Todos los productos</option>';
    for (var i=0;i<brands.length;i++)
    {
        brand = brands[i];
        if (selected_brands.length > 0 && selected_brands[0] != '' && $.inArray(brand['name'], selected_brands) < 0 ) continue;
        products = brand['products'];
        for (var j=0;j<products.length;j++)
        {
            product = products[j];
            options = options + '<option value="' + product['name'] + '">' + product['name'] +' - ' + brand['name'] + '</option>';
        }
    }
    $("#filter_product").html(options);
    search();    
}

function filterTopicChanged()
{
    search();    
}

function filterProductChanged()
{
    search();    
}

function filterCountryChanged()
{
    search();    
}

function filterSentimentChanged()
{
    search();    
}

function search()
{
    search_extended(false);
}

function searchMore()
{
    search_extended(true);
}

function countResults()
{
    filterdict = makeFilterDict();
    filterdict['count_only'] = "true";
    $.ajax({
        url: "/api/feeds/search", 
        data: filterdict, 
        type: "GET",
    }).done(function (response) { 
        alert("Cantidad de Feeds: " + response['count']);
    });
}

function makeFilterDict()
{
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    feedbox = $("#feed-box").addClass("loading_bottom");
    object_id = $("#object_id").val();
    brands_to_include = $("#filter_brand").val();
    filter_product = $("#filter_product").val();
    filter_country = $("#filter_country").val();
    filter_sentiment = $("#filter_sentiment").val();
    filter_topic = $("#filter_topic").val();
    startend = getDateRange();
    start = startend[0].format("YYYY-MM-DD");
    end = startend[1].format("YYYY-MM-DD");
    text = $("#search_text").val();
    filterdict = {"account_id": account_id, 
            'campaign_id': campaign_id, 
            'start': start, 
            'end': end, 
            'text': text,
            'brands_to_include': brands_to_include,
            'filter_product': filter_product,
            'filter_country': filter_country,
            'filter_sentiment': filter_sentiment,
            'filter_topic': filter_topic,
            'object_id': object_id,
            'source_twitter': $('#source_twitter').is(":checked"),
            'source_facebook': $('#source_facebook').is(":checked"),
            'source_forums': $('#source_forums').is(":checked"),
    }
    return filterdict;
}

function search_extended(more)
{   
    if (more)
    {
        skip = $('#feed-box').children().length;
    }
    else
    {
        skip = 0;
    }
    limit = 20;
    filterdict = makeFilterDict();
    filterdict['skip'] = skip;
    filterdict['limit'] = limit;
    $.ajax({
        url: "/api/feeds/search", 
        data: filterdict, 
        type: "GET",
    }).done(function (response) { 
        updateFeedsContent(response, more)
        if (response['feeds'].length == limit)
        {
            $(window).scroll(bindScroll);            
        }
    });
}

function updateFeedsContent(response, more)
{
    feeds = response['feeds'];
    //mentions = 0;
    html = $('#feed_model').html();
    feedbox = $("#feed-box");
    if (!more) feedbox.html("");    
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
        profile_image_url = "src='#'";
        profile_image_style="width: 48px; height: 48px;"
        title = "";
        display_title ="none";
        if ('profile_image_url_https' in feed['user'])
        {
            profile_image_url = "src='"+feed['user']['profile_image_url_https']+"'";
        }
        else
        {
            //profile_image_style = profile_image_style  + " display: none;";
        }
        if (feed['x_feed_type'] == 'facebook')
        {
            title = feed['activity:link:via'];
            display_title ="block";
        }            
        else if (feed['x_feed_type'] == 'forum')
        {
            title = feed['link'];
            display_title ="block";
        }                    
        feed_date = new Date(feed['x_created_at']['$date'])
        country = '';
        if ('x_coordinates' in feed && feed['x_coordinates'] != null) country = feed['x_coordinates']['country'];

        feedtag = $(html.replace("%%_id%%", feed['_id']['$oid'])
                    .replace("%%created_at%%", feed_date)
                    .replace("%%user.name%%", feed['user']['screen_name'])
                    .replace("%%text%%", feed['text'])
                    .replace("%%sentiment%%", sent)
                    .replace("%%sentiment_color%%", color)
                    .replace("%%brand%%", brand)
                    .replace("%%product%%", product)
                    .replace("%%confidence%%", confidence)
                    .replace("%%user.profile_image_url%%", profile_image_url)                    
                    .replace("%%profile_image_style%%", profile_image_style)                    
                    .replace("%%topics%%", topicshtml)
                    .replace("%%feed_url%%", feed_url)
                    .replace("%%user_profile_url%%", user_url)
                    .replace("%%user_profile_url%%", user_url)
                    .replace("%%country%%", country)
                    .replace("%%title%%", title)
                    .replace("%%display_title%%", display_title)
                    );    
        
        feedbox.append(feedtag);
    }
    $("#feed-box").removeClass("loading_bottom");
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

function bindScroll()
{
   if($(window).scrollTop() + $(window).height() > $(document).height() - 100) {
       $(window).unbind('scroll');
       console.log("loading more feeds...");
       searchMore();
   }
}
