$(function(){
	initWidgets();
})

function initWidgets() {
    $(".button").button();
    $(".accordion").accordion( { heightStyle: "content", collapsible: true} );
    $(".tabs").tabs();
    $('.button.remove').button({icons: {primary: 'ui-icon-closethick'},text: false});
    $('input.autocomplete.keywordset_selector').autocomplete({
      source: "/search_keywordset",
      minLength: 2,
      select: function( event, ui ) {  
        if (ui.item) {
            newtag = $('<div class="keywordset"><div id="'+ui.item.id+'" label="'+ui.item.label+'" class="button word">'+ui.item.label+'</div>- <input type="number" class="value" value="1"/><div class="button remove" onclick="$(this).parent().remove()">ELIMINAR</div></div>');
            newtag.find(".button").button();
            //<div id='"+ui.item.id+"' label='"+ui.item.label+"' class='button keywordset'>" + ui.item.label + "</div>").button();
            $(this).parent().find(".keywordsets").append(newtag);
        }
        
      }
    });
}

function refreshWidgets(tag) {
	$(tag).find(".button").button();
    $(tag).find(".accordion").accordion( { heightStyle: "content", collapsible: true} );
    $(tag).find(".tabs").tabs();
	$(tag).find('.button.remove').button({icons: {primary: 'ui-icon-closethick'},text: false});
    $(tag).find('input.autocomplete.keywordset_selector').autocomplete({
      source: "/search_keywordset",
      minLength: 2,
      select: function( event, ui ) {  
        if (ui.item) {
            newtag = $('<div class="keywordset"><div id="'+ui.item.id+'" label="'+ui.item.label+'" class="button word">'+ui.item.label+'</div>- <input type="number" class="value" value="1"/><div class="button remove" onclick="$(this).parent().remove()">ELIMINAR</div></div>');
            newtag.find(".button").button();
            //<div id='"+ui.item.id+"' label='"+ui.item.label+"' class='button keywordset'>" + ui.item.label + "</div>").button();
            $(this).parent().find(".keywordsets").append(newtag);
        }
        
      }
    });
}

$(document).ready(function(){
  $('.jq-button').each(function(){
    var meta=$(this).metadata();
    $(this).button(meta);
  });
});

function addCampaign()
{
    $.ajax({
        url: "/account/campaign/add", 
        data: {"account_id": $('#account_id').val()}, 
        type: "POST",
    }).done(function (campaign_id) { 
		container = $("#"+$('#account_id').val()+"_campaigns_container");
		newtag = $($("#campaign_model").children().html().replace(/##account_id##/g, $('#account_id').val()).replace(/##campaign_id##/g, campaign_id));
		container.append(newtag);
		container.accordion('refresh');
		initWidgets();
	});
    
}

function removeCampaign(campaign_id)
{
    $.ajax({
        url: "/account/campaign/remove", 
        data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id}, 
        type: "POST",
    }).done(function () { 
		var parent = $("#campaign_"+campaign_id);
		var head = parent.prev('h3');
		parent.add(head).fadeOut('slow',function(){$(this).remove();});        				
	});
    
}

function addBrand(campaign_id)
{
    $.ajax({
        url: "/account/campaign/brand/add", 
        data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id}, 
        type: "POST",
    }).done(function (brand_id) {
		container = $("#"+campaign_id+"_brands_container");
		newtag = $($("#brand_model").children().html().replace(/##account_id##/g, $('#account_id').val()).replace(/##brand_id##/g, brand_id).replace(/##campaign_id##/g, campaign_id));
		container.append(newtag);
		container.accordion('refresh');
		initWidgets();		
		
	});
    
}

function removeBrand(campaign_id, brand_id)
{
    $.ajax({
        url: "/account/campaign/brand/remove", 
        data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id, 'brand_id': brand_id}, 
        type: "POST",
    }).done(function () { 
		var parent = $("#brand_"+brand_id);
		var head = parent.prev('h3');
		parent.add(head).fadeOut('slow',function(){$(this).remove();});        		
	});
    
}

function addProduct(campaign_id, brand_id)
{
    $.ajax({
        url: "/account/campaign/brand/product/add", 
        data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id, 'brand_id': brand_id}, 
        type: "POST",
    }).done(function (product_id) {
		container = $("#"+brand_id+"_products_container");
		newtag = $($("#product_model").children().html().replace(/##account_id##/g, $('#account_id').val()).replace(/##brand_id##/g, brand_id).replace(/##campaign_id##/g, campaign_id).replace(/##product_id##/g, product_id));
		container.append(newtag);
		container.accordion('refresh');
		initWidgets();
	});
    
}

function removeProduct(campaign_id, brand_id, product_id)
{
    $.ajax({
        url: "/account/campaign/brand/product/remove", 
        data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id, 'brand_id': brand_id, 'product_id': product_id}, 
        type: "POST",
    }).done(function () { 
		var parent = $("#product_"+product_id);
		var head = parent.prev('h3');
		parent.add(head).fadeOut('slow',function(){$(this).remove();});        
    });
}

function updateCampaignName(campaign_id, value)
{
    $.ajax({
        url: "/account/campaign/update/name", 
        data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id, 'value': value}, 
        type: "POST",
    }).done(function () { 
        //location.reload()
        
    });
}

function updateBrandKeywords(campaign_id, brand_id)
{
    //keywords
    var res = '';
    tags = $('#'+brand_id+'_keyword_container>.brand_keyword');
    res = prepareKeywords(tags);
    updateBrand(campaign_id, brand_id, 'keywords', res);
    //keywordsets
    var res = '';
    tags = $('#'+brand_id+'_keywordset_container>.keywordset');
    res = prepareKeywordSets(tags);
    updateBrand(campaign_id, brand_id, 'keyword_sets', res);    
}

function updateBrand(campaign_id, brand_id, field, value)
{
    $.ajax({
        url: "/account/campaign/brand/update", 
            data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id, 'brand_id': brand_id, 'field': field, 'value': value}, 
        type: "POST",
    }).done(function () { 
      //location.reload()
        
    });
}


function prepareKeywords(tags)
{
    var res = '';
    and = ''
    for (var i=0;i<tags.length;i++)
    {
        tag = tags[i];
        if ($(tag).find(".word").val() != '')
        {
            v = $(tag).find(".value").val();
            if (v == '')  v = 0;
            res = res + and + $(tag).find(".word").val() + "%" + v;
            and = '|';
        }
    }    
    return res;
}

function prepareKeywordSets(tags)
{
    var res = '';
    and = ''
    for (var i=0;i<tags.length;i++)
    {
        tag = tags[i];
        buttontag = $(tag).find(".word")
        valuetag = $(tag).find(".value")
        if (buttontag.attr("id") != '')
        {
            v = valuetag.val();
            if (v == '')  v = 0;
            res = res + and + buttontag.attr("id") + "%" + buttontag.attr("label") + "%" + v ;
            and = '|';
        }
    }    
    return res;
}

function prepareIdRules(tags)
{
    var res = '';
    and = ''
    for (var i=0;i<tags.length;i++)
    {
        tag = tags[i];
        if ($(tag).find(".phrase").val() != '')
        {
            res = res + and + $(tag).find(".phrase").val();
            and = '|';
        }
    }    
    return res;
}

function updateProductKeywords(campaign_id, brand_id, product_id)
{
    var res = '';
    tags = $('#'+product_id+'_keyword_container>.product_keyword');
    res = prepareKeywords(tags);
    updateProduct(campaign_id, brand_id, product_id, 'keywords', res);
    //keywordsets
    var res = '';
    tags = $('#'+product_id+'_keywordset_container>.keywordset');
    res = prepareKeywordSets(tags);
    updateProduct(campaign_id, brand_id, product_id, 'keyword_sets', res);    
    
}

function updateBrandIdRules(campaign_id, brand_id)
{
    var res = '';
    tags = $('#'+brand_id+'_identification_rules_container>.brand_id_rule');
    res = prepareIdRules(tags);
    updateBrand(campaign_id, brand_id, 'identification_rules', res);
}

function updateProductIdRules(campaign_id, brand_id, product_id)
{
    var res = '';
    tags = $('#'+product_id+'_identification_rules_container>.product_id_rule');
    res = prepareIdRules(tags);
    updateProduct(campaign_id, brand_id, product_id, 'identification_rules', res);
}

function updateProduct(campaign_id, brand_id, product_id, field, value)
{
    $.ajax({
        url: "/account/campaign/brand/product/update", 
            data: {"account_id": $('#account_id').val(), 'campaign_id': campaign_id, 'brand_id': brand_id, 'product_id': product_id, 'field': field, 'value': value}, 
        type: "POST",
    }).done(function () { 
        //location.reload()
        
    });
}

function checkLastItemChanged(input)
{
    var div = $(input).parent();
    if ($(div).attr("last") == "true")
    {
        newdiv = $(div).clone();
        $(div).attr("last", "false");
        $(newdiv).find("input").val("");
        $(div).parent().append(newdiv)
    }
}

