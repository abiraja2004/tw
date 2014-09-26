var deb_var=null;
var deb_var2=null;

$(function () {   
    $('#tweet-box').slimScroll({
        height: '705px'
    });
        
    tweets_count_group_by = "day";
    $(".tweet_count_group_by").click(function (e) { 
        tweets_count_group_by = $(this).attr('group_by') 
        fetchTweetsCount('brand');
        fetchTweetsCount('product');
    });
    
});

function dateRangeChanged()
{
    account_id = $('[fn=a_id]').val();;
    campaign_id = $('[fn=c_id]').val();
    
    fetchTweets(account_id, campaign_id, true);
    fetchTweetsCount('brand');
    fetchTweetsCount('product');
    //fetchAnalyticsSessions();
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
        $('#analytics_sessions').html(response['res']);
    });   
}