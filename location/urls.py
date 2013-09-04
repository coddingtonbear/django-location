from django.conf.urls.defaults import patterns, url

urlpatterns = patterns(
    'location.views',
    url(r'^foursquare/', 'foursquare_checkin', name='foursquare_push'),
)
