var keywordsets_blookhound=null;

$(document).ready(function () {   
    $('.slider').slider()
    $('.slider').css("width", "100%");
    
    
keywordsets_blookhound = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  prefetch: '/api/keywordset/prefetch',
  remote: '/api/keywordset/search?term=%QUERY'
});
 
// kicks off the loading/processing of `local` and `prefetch`
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
    }).on("typeahead:autocompleted", function () {checkLastItemChanged(this)});
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
    pt = $(products_container.children()[0]).clone();
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

function removeBrand(tag)
{
    $(tag).closest(".brand").remove();
}

function saveCampaign()
{
    brands = $(".brand");
    campaign = {'brands': {}}
    for (var i = 0; i<brands.length; i++)
    {
        tagbrand = $(brands[i]);
        if (tagbrand.attr("brand_model") == "true") continue;
        brand = {};
        brand['name'] = tagbrand.find("[fn=bname]").html();
        brand['synonyms'] = tagbrand.find("[fn=bsynonyms]").val();
        brand['rules'] = []
        tags = tagbrand.find("[fn=brule]");
        for (j=0;j<tags.length;j++)
        {
            if ($(tags[j]).val() != "") brand['rules'].push($(tags[j]).val());
        }
        brand['keyword_sets'] = []
        tags = tagbrand.find("[fn=bkwset]");
        for (j=0;j<tags.length;j++)
        {
            if ($(tags[j]).find("[fn=bkws]").val() != "") 
            {   
                brand['keyword_sets'].push([$(tags[j]).find("[fn=bkws]").val(), $(tags[j]).find("[fn=value]").data('slider').getValue()]);
            }
        }
        campaign['brands'][brand['name']] = brand;
    }
    return campaign;
}