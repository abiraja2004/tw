var keywordsets_blookhound=null;
var deb_var = null;
var deb_var2 = null;

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
        checkLastItemChanged(this);
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

function addKeywordset(tag)
{
    keywordsets_container = $(tag).closest(".keywordsets_section_container").find(".keywordsets_container");
    deb_var =keywordsets_container;
    bt = $(keywordsets_container.children()[0]).clone();
    deb_var2 = bt;
    keywordsets_container.append(bt);
    bt.css("display", "block");
    $(bt).find(".pre_slider").removeClass('pre_slider').addClass('slider').slider();
    $(bt).find(".slider").css("width", "100%");
    $(bt).find(".pre_pre_slider").removeClass('pre_pre_slider').addClass('pre_slider');
    $(bt).find(".pre_pre_pre_slider").removeClass('pre_pre_pre_slider').addClass('pre_pre_slider');
    
    setupTypeahead($(bt).find(".pre_typeahead").removeClass('pre_typeahead').addClass('typeahead'))    
    $(bt).find(".pre_pre_typeahead").removeClass('pre_pre_typeahead').addClass('pre_typeahead');
    $(bt).find(".pre_pre_pre_typeahead").removeClass('pre_pre_pre_typeahead').addClass('pre_pre_typeahead');
    getNewId(function (id) {
        bt.find(".keywordset_container").attr('id', id);
        bt.find(".keywordset_title").attr('href', "#"+id);
    });
}



function saveKeywordset(button)
{
    container = $(button).closest(".keywordset").find(".keywordset_container");
    kwset = {};
    deb_var2 = container;
    kwset_id = container.attr('id');
    kwset['name'] = container.find("[fn=name]").val();
    kwset['keywordsets'] = []
    tags = container.find("[fn=keywordset]");
    for (j=1;j<tags.length;j++)
    {
        tags2 = tags[j];
        if ($(tags2).find("[fn=word]").typeahead('val') != "") 
        {   
            d = {}
            d['name'] = $(tags2).find("[fn=word]:not([kwset_id=''])").typeahead('val');
            d['_id'] = $(tags2).find("[fn=word]:not([kwset_id=''])").attr("kwset_id")
            kwset['keywordsets'].push(d);
        }
    }
    kwset['keywords'] = []
    tags = container.find("[fn=keyword]");
    for (j=1;j<tags.length;j++)
    {

        tags2 = tags[j];
        if ($(tags2).find("[fn=word]").val() != "") 
        {   
            kwset['keywords'].push($(tags2).find("[fn=word]").val());
        }
    }        
    data = {}
    data['keywordset_id'] = kwset_id;
    data['keywordset'] = kwset;
    deb_var = kwset;
    $.ajax({
            url: "/api/account/keywordset/save", 
            contentType: 'application/json',
            dataType: 'json',
            data: JSON.stringify(data), 
            type: "POST",
            processData: false,
        }).done(function (response) {
            alert("Grupo grabado")
        });   
    return data;
}