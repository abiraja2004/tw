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
    
    $(".captured_data_table").dataTable({
                    "bPaginate": true,
                    "bLengthChange": false,
                    "bFilter": false,
                    "bSort": true,
                    "bInfo": true,
                    "bAutoWidth": false
                });
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
        account_id = $('[fn=a_id]').val();;
        campaign_id = $('[fn=c_id]').val();
        pt.find(".datacollection_container").attr('id', id);
        pt.find(".datacollection_title").attr('href', "#"+id);
        pt.find("[fn=dc_landing_page]").attr("href", "/dc/"+account_id+"/"+campaign_id+"/"+id);
    });
}     

function saveDatacollection(tag)
{    
    
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
    
    console.debug(object);
    data = {};
    data['datacollection'] = object;
    data['datacollection_id'] = object_id;
    data['account_id'] = $('[fn=a_id]').val();
    
    $.ajax({
            url: "/api/account/datacollection/save", 
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