var deb_var = null;
var deb_var2 = null;

$(document).ready(function () {   
    $('.slider').slider()
    $('.slider').css("width", "100%");
});
    
    
function dateRangeChanged()
{

}



function addUser(tag)
{
    users_container = $(tag).closest(".users_section_container").find(".users_container");
    deb_var =users_container;
    bt = $(users_container.children()[0]).clone();
    deb_var2 = bt;
    bt.find("[fn=p_id]").removeClass("collapse");
    users_container.append(bt);
    bt.css("display", "block");

    getNewId(function (id) {
        bt.find(".user_container").attr('id', id);
        bt.find(".user_title").attr('href', "#"+id);
    });
}


function addAccount(tag)
{
    accounts_container = $(tag).closest(".accounts_section_container").find(".accounts_container");
    deb_var =accounts_container;
    bt = $(accounts_container.children()[0]).clone();
    deb_var2 = bt;
    accounts_container.append(bt);
    bt.css("display", "block");

    getNewId(function (id) {
        bt.find(".account_container").attr('id', id);
        bt.find(".account_name").attr('href', "#"+id);
    });
}

function addCampaign(tag)
{
    campaigns_container = $(tag).closest(".campaigns_section_container").find(".campaigns_container");
    deb_var =campaigns_container;
    bt = $(campaigns_container.children()[0]).clone();
    deb_var2 = bt;
    bt.find("[fn=p_id]").removeClass("collapse");
    campaigns_container.append(bt);
    bt.css("display", "block");

    getNewId(function (id) {
        bt.find(".campaign_container").attr('id', id);
        bt.find(".campaign_title").attr('href', "#"+id);
    });
}

function createTwDateIndex(tag)
{
    campaign_id = $(tag).closest("[fn=c_id").attr("id");
    $.ajax({
            url: "/api/create_index", 
            data: {"collection_name": "tweets_"+campaign_id, "fields": "x_created_at,1"}, 
            type: "POST",
        }).done(function (response) {
            alert(response['result'])
        });   
}

function createTwTextIndex(tag)
{
    campaign_id = $(tag).closest("[fn=c_id").attr("id");
    $.ajax({
            url: "/api/create_index", 
            data: {"collection_name": "tweets_"+campaign_id, "fields": "text,text"}, 
            type: "POST",
        }).done(function (response) {
            alert(response['result'])
        });   
}

function saveAccount(button)
{
    container = $(button).closest(".account").find(".account_container");
    account = {};
    deb_var2 = container;
    account_id = container.attr('id');
    account['name'] = container.find("[fn=name]").val();


    account['users'] = {};
    users = container.find(".user");
    for (k=1;k<users.length;k++)
    {
        taguser = $(users[k]);
        user = {};
        user['username'] = taguser.find("[fn=uname]").val();
        user['password'] = taguser.find("[fn=upassword]").val();
        user['access'] = taguser.find("[fn=uaccess]").val();
        account['users'][user['username']] = user;
    }

    account['campaigns'] = {};
    campaigns = container.find(".campaign");
    for (k=1;k<campaigns.length;k++)
    {
        tagcampaign = $(campaigns[k]);
        campaign = {};
        campaign['_id'] = tagcampaign.find("[fn=c_id]").attr('id');
        campaign['name'] = tagcampaign.find("[fn=cname]").val();
        account['campaigns'][campaign['_id']] = campaign;
    }
    
    data = {};
    data['account_id'] = account_id;
    data['account'] = account;
    deb_var = data;
    $.ajax({
            url: "/api/account/save", 
            contentType: 'application/json',
            dataType: 'json',
            data: JSON.stringify(data), 
            type: "POST",
            processData: false,
        }).done(function (response) {
            alert("Cuenta grabada")
        });   
    return data;
}