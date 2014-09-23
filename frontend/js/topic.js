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

function addTopic(tag)
{
    topics_container = $(tag).closest(".topics_section_container").find(".topics_container");
    deb_var =topics_container;
    bt = $(topics_container.children()[0]).clone();
    deb_var2 = bt;
    topics_container.append(bt);
    bt.css("display", "block");
    $(bt).find(".pre_slider").removeClass('pre_slider').addClass('slider').slider();
    $(bt).find(".slider").css("width", "100%");
    $(bt).find(".pre_pre_slider").removeClass('pre_pre_slider').addClass('pre_slider');
    $(bt).find(".pre_pre_pre_slider").removeClass('pre_pre_pre_slider').addClass('pre_pre_slider');
    
    setupTypeahead($(bt).find(".pre_typeahead").removeClass('pre_typeahead').addClass('typeahead'))    
    $(bt).find(".pre_pre_typeahead").removeClass('pre_pre_typeahead').addClass('pre_typeahead');
    $(bt).find(".pre_pre_pre_typeahead").removeClass('pre_pre_pre_typeahead').addClass('pre_pre_typeahead');
    getNewId(function (id) {
        bt.find(".topic_container").attr('id', id);
        bt.find(".topic_title").attr('href', "#"+id);
    });
}



function saveTopic(button)
{
    container = $(button).closest(".topic").find(".topic_container");
    topic = {};
    deb_var2 = container;
    topic_id = container.attr('id');
    topic['name'] = container.find("[fn=name]").val();
    topic['keywordsets'] = []
    tags = container.find("[fn=keywordset]");
    for (j=1;j<tags.length;j++)
    {
        tags2 = tags[j];
        if ($(tags2).find("[fn=word]").typeahead('val') != "") 
        {   
            d = {}
            d['name'] = $(tags2).find("[fn=word]:not([kwset_id='']):not([readonly])").typeahead('val');
            d['value'] = $(tags2).find("[fn=value]:not([kwset_id='']:not([readonly]))").data('slider').getValue();
            d['_id'] = $(tags2).find("[fn=word]:not([kwset_id='']):not([readonly])").attr("kwset_id")
            topic['keywordsets'].push(d);
        }
    }
    topic['keywords'] = []
    tags = container.find("[fn=keyword]");
    for (j=1;j<tags.length;j++)
    {

        tags2 = tags[j];
        if ($(tags2).find("[fn=word]").val() != "") 
        {   
            topic['keywords'].push([$(tags2).find("[fn=word]").val(), $(tags2).find("[fn=value]").data('slider').getValue()]);
        }
    }        
    data = {}
    data['topic_id'] = topic_id;
    data['topic'] = topic;
    deb_var = topic;
    $.ajax({
            url: "/api/account/topic/save", 
            contentType: 'application/json',
            dataType: 'json',
            data: JSON.stringify(data), 
            type: "POST",
            processData: false,
        }).done(function (response) {
            alert("Tema grabado")
        });   
    return data;
}