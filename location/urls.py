from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('location.views',
        url(r'^foursquare/', 'foursquare_checkin', ),
        url(r'^kml/', 'get_kml', ),
        url(r'^$', 'my_location', ),
    )
