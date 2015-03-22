var deb_var = null;

function dateRangeChanged()
{
}


function fetchFollowers(button)
{
    deb_var = button;
    row = $($(button).closest(".row"))
    account_id = $('[fn=a_id]').val();;

    params = {};
    params['account_id'] = account_id;
    params['tags'] =  row.find("[fn=tag]").val();
    params['twitter_accounts'] = row.find("[fn=fetch_followers_from]").val();
    $("#person-box").addClass("loading_bottom");

    $.ajax({
           url: "/api/persons/fetch_followers",
           data: params,
           type: "GET",
           }).done(function (response)
                   {
                        deb_var = response;
                        fillPersonsTable(response['users'])
                   });
}

function addTag(button)
{
    $('#persons-box').find('.item').find('.tags').append($('<small class="badge pull-left bg-olive" tag="'+$("[fn=tag]").val()+'">' + $("[fn=tag]").val() + '</small>'));
}

function removeTag(button)
{
    $('#persons-box').find('small[tag='+$("[fn=tag]").val()+']').remove()
}

function removePerson(btn)
{
    //if (!window.confirm("Estás seguro que quieres eliminar esta persona?")) return
    account_id = $('[fn=a_id]').val();
    campaign_id = $('[fn=c_id]').val();
    item = $(btn).closest(".item");
    feed_object_id = item.find("input[name=id]").val();
    item.hide(500);
}

function fillPersonsTable(persons, more)
{
    html = $('#person_model').html();
    personbox = $("#persons-box");
    if (!more) personbox.html("");
    for (var i=0;i<persons.length;i++)
    {
        person = persons[i];
        profile_image_url = "src='#'";
        if ('profile_image_url' in person)
        {
            profile_image_url = "src='"+person['profile_image_url']+"'";
        }
        tags = "";
        if ('x_tags' in person) tags = person['x_tags'];

        persontag = $(html.replace("%%_id%%", '@' + person['screen_name'])
                    .replace("%%name%%", person['name'])
                    .replace("%%screen_name%%", person['screen_name'])
                    .replace("%%profile_image_url%%", profile_image_url)
                    .replace("%%tags%%", tags)
                    );

        personbox.append(persontag);
    }
    $("#person-box").removeClass("loading_bottom");
    //$('#mentions_indicator').html(''+mentions);
}

function savePersons(btn)
{
    persons = $('.item');
    html = "<table>";
    for (var i = 1; i<persons.length; i++)
    {
        html += "<tr><td>" + $(persons[i]).find("[fn=screen_name]").html() + "</td><td>" + $(persons[i]).find("[fn=name]").html() + "</td></tr>";
    }
    html += "</table>";
    $(window.open().document.body).html(html);
}