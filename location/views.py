import datetime
import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.gis.geos import Point
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from lxml import etree
import pytz
from social_auth.models import UserSocialAuth

from location import models


@staff_member_required
def my_location(request):
    try:
        most_recent_location = (
            models.LocationSnapshot.objects.order_by('-date')[0]
        )
    except IndexError:
        most_recent_location = None
    return TemplateResponse(
        request,
        'location/my_location.html',
        {
            'location': most_recent_location
        }
    )


@staff_member_required
def get_kml(request):
    from pykml.factory import KML_ElementMaker as KML
    timezone = pytz.timezone(
        request.GET.get('timezone', 'America/Los_Angeles')
    )
    date_string = request.GET.get('date', None)
    if date_string is None:
        begin_date = timezone.localize(
            datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        )
    else:
        year, month, day = date_string.split('-')
        begin_date = datetime.datetime(
            int(year), int(month), int(day)
        ).replace(tzinfo=pytz.UTC)
    end_date = begin_date + datetime.timedelta(days=1)
    placemarks = []
    icon_styles = []
    coord_string = ""
    points = models.LocationSnapshot.objects.filter(
        date__gt=begin_date,
        date__lte=end_date
    ).select_related().order_by('date').iterator()
    source_types = models.LocationSourceType.objects.all()
    for source_type in source_types:
        if source_type.icon:
            icon_styles.append(
                KML.IconStyle(
                    KML.scale(1.0),
                ),
                KML.Icon(
                    KML.href(settings.MEDIA_URL + source_type.icon.url)
                ),
                id="type%s" % source_type.id
            )
    for point in points:
        coord_string = (
            coord_string + str(point.location.coords[0])
            + "," + str(point.location.coords[1]) + " "
        )
        placemarks.append(
            KML.Placemark(
                KML.description("%s" % (point, )),
                KML.styleUrl("#type%s" % point.source.type.id),
                KML.Point(
                    KML.coordinates(
                        str(point.location.coords[0]) + ","
                        + str(point.location.coords[1])
                    )
                )
            )
        )
    style = KML.Style(
        *icon_styles,
        id='default'
    )
    path = KML.Placemark(
        KML.name("Path"),
        KML.LineString(
            KML.coordinates(
                coord_string
            )
        )
    )
    document = KML.kml(
        KML.Document(
            KML.name('My recent path'),
            * [style] + [path] + placemarks
        )
    )
    response = HttpResponse(
        etree.tostring(document, pretty_print=True),
        mimetype='application/vnd.google-earth.kml+xml'
    )
    response['Content-Disposition'] = 'attachment; filename=%s.kml' % (
        datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
    )

    return response


@csrf_exempt
def foursquare_checkin(request):
    (source, created, ) = (
        models.LocationSourceType.objects.get_or_create(
            name='Foursquare Check-in'
        )
    )
    raw_data = request.POST.get('checkin', None)
    data = json.loads(raw_data)
    if data['type'] == 'checkin':
        checkin = models.LocationSource()
        checkin.name = data['venue']['name']
        checkin.type = source
        checkin.data = raw_data
        checkin.save()

        socialauth = UserSocialAuth.objects.get(
            uid=data['user']['id'],
            provider='foursquare'
        )

        snapshot = models.LocationSnapshot()
        snapshot.user = socialauth.user
        snapshot.location = Point(
            data['venue']['location']['lng'],
            data['venue']['location']['lat'],
        )
        snapshot.source = checkin
        snapshot.save()
    return HttpResponse("OK")
