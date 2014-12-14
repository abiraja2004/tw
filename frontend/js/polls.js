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
    monitor_dateRangeChanged();
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


function savePoll(container)
{    
    deb_var = container;
    poll = {};
    poll_id = container.find('[fn=p_id]').attr('id');
    poll['name'] = container.find('[fn=name]').val();
    poll['poll_hashtag'] = container.find('[fn=poll_hashtag]').val();
    poll['hashtags'] = container.find('[fn=hashtags]').val();
    console.debug(poll);
    data = {};
    data['poll'] = poll;
    data['poll_id'] = poll_id;
    data['account_id'] = $('[fn=a_id]').val();
    
    $.ajax({
            url: "/api/account/poll/save", 
            contentType: 'application/json',
            dataType: 'json',
            data: JSON.stringify(data), 
            type: "POST",
            processData: false,
        }).done(function (response) {
            alert("Encuesta grabada")
        });   
    
    return data;
}