$(function () {   
    $('.slider').slider();
});

function dateRangeChanged()
{

}



function checkLastItemChanged(input)
{
    var div = $(input).parent().closest("div");
    if ($(div).attr("last") == "true")
    {
        newdiv = $(div).clone();
        $(div).attr("last", "false");
        $(newdiv).find("input").val("");
        $(div).parent().append(newdiv)
    }
}


function addProduct(tag)
{
    products_container = $(tag).closest(".products_section_container").find(".products_container");
    producttag = products_container.find("[product_model=true]");
    pt = products_container.find("[product_model=true]").clone();
    pt.removeAttr("style");
    pt.removeAttr("product_model");
    pt.find(".pre_slider").button().slider();
    products_container.append(pt);
}

function removeProduct(tag)
{
    $(tag).closest(".product").remove();
}

function removeBrand(tag)
{
    $(tag).closest(".brand").remove();
}