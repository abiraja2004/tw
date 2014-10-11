var keywordsets_blookhound=null;
var deb_var = null;
$(document).ready(function () {   
    $('.slider').slider()
    $('.slider').css("width", "100%");
    
    
keywordsets_blookhound = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  prefetch: '/api/keywordset/prefetch',
  remote: '/api/keywordset/search?term=%QUERY'
});

keywordsets_blookhound.initialize();
setupTypeahead($('.typeahead'));

});

function dateRangeChanged()
{

}

function setupTypeahead(tags)
{
    tags.typeahead(null, {
    name: 'keywordsets',
    displayKey: 'value',
    source: keywordsets_blookhound.ttAdapter()
    }).on("typeahead:selected typeahead:autocompleted", function (e, datum) {
        $(this).attr("kwset_id",datum.id);
        checkLastItemChanged(this)
    });
}

function checkLastItemChanged(input)
{
    var div = $(input).parent().closest("div");
    if ($(div).is(":last-child"))
    {
        newdiv = $($(div).parent().children()[0]).clone()
        $(newdiv).find("input").val("");
        $(newdiv).css("display", "block");
        $(div).parent().append(newdiv)  
        $(newdiv).find(".pre_slider").removeClass('pre_slider').addClass('slider').slider();        
        setupTypeahead($(newdiv).find(".pre_typeahead").removeClass('pre_typeahead').addClass('typeahead'))
    }
}


function addProduct(btn)
{
    products_container = $(btn).closest(".products_section_container").find(".products_container");
    deb_var = products_container;
    pt = $(products_container.children()[0]).clone();
    //deb_var = pt;
    //pt = products_container.find("[product_model=true]").clone();
    products_container.append(pt);    
    pt.css("display", "block");
    //pt.find(".pre_slider").button().slider();
    $(pt).find(".pre_slider").removeClass('pre_slider').addClass('slider').slider();
    $(pt).find(".slider").css("width", "100%");
    $(pt).find(".pre_pre_slider").removeClass('pre_pre_slider').addClass('pre_slider');

    setupTypeahead($(pt).find(".pre_typeahead").removeClass('pre_typeahead').addClass('typeahead'))    
    $(pt).find(".pre_pre_typeahead").removeClass('pre_pre_typeahead').addClass('pre_typeahead');
    getNewId(function (id) {
        pt.find(".product_container").attr('id', id);
        pt.find(".product_title").attr('href', "#"+id);
    });
}

function addBrand(tag)
{
    brands_container = $(tag).closest(".brands_section_container").find(".brands_container");
    bt = $(brands_container.children()[0]).clone();
    brands_container.append(bt);    
    bt.css("display", "block");
    $(bt).find(".pre_slider").removeClass('pre_slider').addClass('slider').slider();
    $(bt).find(".slider").css("width", "100%");
    $(bt).find(".pre_pre_slider").removeClass('pre_pre_slider').addClass('pre_slider');
    $(bt).find(".pre_pre_pre_slider").removeClass('pre_pre_pre_slider').addClass('pre_pre_slider');
    
    setupTypeahead($(bt).find(".pre_typeahead").removeClass('pre_typeahead').addClass('typeahead'))    
    $(bt).find(".pre_pre_typeahead").removeClass('pre_pre_typeahead').addClass('pre_typeahead');
    $(bt).find(".pre_pre_pre_typeahead").removeClass('pre_pre_pre_typeahead').addClass('pre_pre_typeahead');
    getNewId(function (id) {
        bt.find(".brand_container").attr('id', id);
        bt.find(".brand_title").attr('href', "#"+id);
    });
}

function addPoll(tag)
{
    polls_container = $(tag).closest(".polls_section_container").find(".polls_container");
    console.debug(polls_container);
    pt = $(polls_container.children()[0]).clone();
    console.debug(pt);
    polls_container.append(pt);    
    pt.css("display", "block");
    $(pt).find(".pre_slider").removeClass('pre_slider').addClass('slider').slider();
    $(pt).find(".slider").css("width", "100%");
    $(pt).find(".pre_pre_slider").removeClass('pre_pre_slider').addClass('pre_slider');
    $(pt).find(".pre_pre_pre_slider").removeClass('pre_pre_pre_slider').addClass('pre_pre_slider');
    
    setupTypeahead($(pt).find(".pre_typeahead").removeClass('pre_typeahead').addClass('typeahead'))    
    $(pt).find(".pre_pre_typeahead").removeClass('pre_pre_typeahead').addClass('pre_typeahead');
    $(pt).find(".pre_pre_pre_typeahead").removeClass('pre_pre_pre_typeahead').addClass('pre_pre_typeahead');
    getNewId(function (id) {
        pt.find(".poll_container").attr('id', id);
        pt.find(".poll_title").attr('href', "#"+id);
    });
}

function addDatacollection(tag)
{
    datacollections_container = $(tag).closest(".datacollections_section_container").find(".datacollections_container");
    pt = $(datacollections_container.children()[0]).clone();
    datacollections_container.append(pt);    
    pt.css("display", "block");
    $(pt).find(".pre_slider").removeClass('pre_slider').addClass('slider').slider();
    $(pt).find(".slider").css("width", "100%");
    $(pt).find(".pre_pre_slider").removeClass('pre_pre_slider').addClass('pre_slider');
    $(pt).find(".pre_pre_pre_slider").removeClass('pre_pre_pre_slider').addClass('pre_pre_slider');
    
    setupTypeahead($(pt).find(".pre_typeahead").removeClass('pre_typeahead').addClass('typeahead'))    
    $(pt).find(".pre_pre_typeahead").removeClass('pre_pre_typeahead').addClass('pre_typeahead');
    $(pt).find(".pre_pre_pre_typeahead").removeClass('pre_pre_pre_typeahead').addClass('pre_pre_typeahead');
    getNewId(function (id) {
        account_id = $('[fn=c_id]').val();;
        campaign_id = $('[fn=a_id]').val();
        pt.find(".datacollection_container").attr('id', id);
        pt.find(".datacollection_title").attr('href', "#"+id);
        pt.find("[fn=dc_landing_page]").attr("href", "/dc/"+account_id+"/"+campaign_id+"/"+id);
    });
}


function saveCampaign()
{    
    campaign = {}
    campaign['name'] = $('[fn=cname]').val();
    campaign['active'] = $("[fn=cactive]").is(':checked');
    campaign['brands'] = {}
    campaign['polls'] = {}
    campaign['datacollections'] = {}
    campaign['analytics'] = {}
    campaign['analytics']['profiles'] = [];
    profiles =  $("[fn=analytics_profile]");
    for (var i = 0;i<profiles.length; i++)
    {
        profile = $(profiles[i]);
        if (profile.is(':checked')) campaign['analytics']['profiles'].push(profile.attr('profile_id'));
    }
    brands = $(".brand");   
    for (var i = 1; i<brands.length; i++)
    {
        tagbrand = $(brands[i]);
        brand = {};
        brand_id = tagbrand.find("[fn=b_id]").attr('id');
        brand['name'] = tagbrand.find("[fn=bname]").html();
        brand['synonyms'] = tagbrand.find("[fn=bsynonyms]").val();
        brand['follow_accounts'] = tagbrand.find("[fn=bfollow_accounts]").val();
        brand['own_brand'] = (tagbrand.find("[fn=bown_brand]:checked").val() != 'false');
        brand['identification_rules'] = []
        tags = tagbrand.find("[fn=brule]");
        for (j=1;j<tags.length;j++)
        {
            if ($(tags[j]).val() != "") brand['identification_rules'].push($(tags[j]).val());
        }
        brand['keyword_sets'] = []
        tags = tagbrand.find("[fn=bkwset]");
        for (j=1;j<tags.length;j++)
        {
            tags2 = tags[j];
            if ($(tags2).find("[fn=word]").typeahead('val') != "") 
            {   
                d = {}
                d['name'] = $(tags2).find("[fn=word]:not([kwset_id='']):not([readonly])").typeahead('val');
                d['value'] = $(tags2).find("[fn=value]:not([kwset_id='']):not([readonly])").data('slider').getValue();
                d['_id'] = $(tags2).find("[fn=word]:not([kwset_id='']):not([readonly])").attr("kwset_id")
                brand['keyword_sets'].push(d);
            }
        }
        brand['keywords'] = []
        tags = tagbrand.find("[fn=bkw]");
        for (j=1;j<tags.length;j++)
        {
            tags2 = tags[j];
            if ($(tags2).find("[fn=word]").val() != "") 
            {   
                brand['keywords'].push([$(tags2).find("[fn=word]").val(), $(tags2).find("[fn=value]").data('slider').getValue()]);
            }
        }        
        
        brand['products'] = {};
        products = tagbrand.find(".product");
        for (k=1;k<products.length;k++)
        {
            tagproduct = $(products[k]);
            product = {}
            product_id = tagproduct.find("[fn=p_id]").attr('id');
            product['name'] = tagproduct.find("[fn=pname]").html();
            product['synonyms'] = tagproduct.find("[fn=psynonyms]").val();
            product['use_brand_id_rules'] = tagproduct.find("[fn=puse_brand_id_rules]").is(':checked');
            product['identification_rules'] = []
            
            tags = tagproduct.find("[fn=prule]");
            for (m=1;m<tags.length;m++)
            {
                if ($(tags[m]).val() != "") product['identification_rules'].push($(tags[m]).val());
            }
            product['keyword_sets'] = []
            tags = tagproduct.find("[fn=pkwset]");
            for (m=1;m<tags.length;m++)
            {
                tags2 = tags[m];
                if ($(tags2).find("[fn=word]").typeahead('val') != "") 
                {   
                    d = {}
                    d['name'] = $(tags2).find("[fn=word]:not([kwset_id='']):not([readonly])").typeahead('val');
                    d['value'] = $(tags2).find("[fn=value]:not([kwset_id='']):not([readonly])").data('slider').getValue();
                    d['_id'] = $(tags2).find("[fn=word]:not([kwset_id='']):not([readonly])").attr("kwset_id")
                    product['keyword_sets'].push(d);
                }
            }
            product['keywords'] = []
            tags = tagproduct.find("[fn=pkw]");
            for (m=1;m<tags.length;m++)
            {
                tags2 = tags[m];
                if ($(tags2).find("[fn=word]").val() != "") 
                {   
                    product['keywords'].push([$(tags2).find("[fn=word]").val(), $(tags2).find("[fn=value]").data('slider').getValue()]);
                }
            }              
            brand['products'][product_id] = product;
        }
        
        campaign['brands'][brand_id] = brand;
    }
    polls = $(".poll");   
    for (var i = 1; i<polls.length; i++)
    {
        tagpoll = $(polls[i]);
        poll = {};
        poll_id = tagpoll.find("[fn=p_id]").attr('id');
        poll['name'] = tagpoll.find("[fn=name]").html();
        poll['hashtags'] = tagpoll.find("[fn=hashtags]").val();
        campaign['polls'][poll_id] = poll;
    }    
    objects = $(".datacollection");   
    for (var i = 1; i<objects.length; i++)
    {
        tag = $(objects[i]);
        object = {};
        object_id = tag.find("[fn=dc_id]").attr('id');
        object['name'] = tag.find("[fn=name]").html();
        object['title'] = tag.find("[fn=title]").val();
        
        object['fields'] = []
        tags = tag.find("[fn=field]");
        for (j=1;j<tags.length;j++)
        {
            tags2 = tags[j];
            if ($(tags2).find("[fn=name]").val() != "") 
            {   
                object['fields'].push({'name': $(tags2).find("[fn=name]").val(), 'label': $(tags2).find("[fn=label]").val(), 'type': $(tags2).find("[fn=type]").val(), 'options': $(tags2).find("[fn=options]").val()});
            }
        }
        
        campaign['datacollections'][object_id] = object;
    }        
    data = {}
    data['campaign'] = campaign;
    data['campaign_id'] = $('[fn=c_id]').val();;
    data['account_id'] = $('[fn=a_id]').val();
    
    $.ajax({
            url: "/api/account/campaign/save", 
            contentType: 'application/json',
            dataType: 'json',
            data: JSON.stringify(data), 
            type: "POST",
            processData: false,
        }).done(function (response) {
            alert("Campaña grabada")
        });   
    
    return data;
}