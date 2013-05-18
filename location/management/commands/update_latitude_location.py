import datetime
import json
import logging
import time

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
import pytz
import requests
from social_auth.models import UserSocialAuth

from location.models import LocationSourceType, LocationSource, LocationSnapshot

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


MIN_ACCURACY = getattr(
    settings,
    'DJANGO_LOCATION_LATITUDE_MIN_ACCURACY',
    20
) # Lower is better


class LocationUnavailableException(Exception):
    pass


class Command(BaseCommand):
    args = '<django.contrib.auth.models.User.username>'
    help = 'Polls the Google Latitude API to gather the specified user\s last '\
            + 'known location.'

    @transaction.commit_on_success
    def handle(self, *args, **kwargs):
        user = User.objects.get(username = args[0])
        auth = UserSocialAuth.objects.get(
                    user = user,
                    provider = 'google-oauth2'
                )
        data = auth.extra_data

        if 'expiration_date' not in data.keys():
            data['expiration_date'] = 0
        if data['expiration_date'] < time.mktime(datetime.datetime.now().timetuple()):
            data = self.refresh_access_token(data)

        latitude_data = self.get_current_location(data)

        self.update_location(latitude_data, user)

        auth.extra_data = data
        auth.save()

    def location_is_accurate(self, data):
        if data['data']['accuracy'] > MIN_ACCURACY:
            logger.info(
                'Accuracy insufficient (> %s)',
                MIN_ACCURACY
            )
            return False
        return True

    def update_location(self, data, user):
        (source_type, created) = LocationSourceType.objects.get_or_create(name='Google Latitude')
        if not self.location_is_accurate(data):
            raise LocationUnavailableException(
                'Latitude location is either out-of-date or too inaccurate.'
            )

        local_tz = pytz.timezone('US/Pacific-New')
        date = datetime.datetime.fromtimestamp(
                    float(data['data']['timestampMs']) / 1000,
                    local_tz
                )

        existing_points = LocationSnapshot.objects.filter(
                    date__gt = date - datetime.timedelta(minutes=1),
                    source__type = source_type
                )
        if existing_points:
            logging.info("Our latest point is %s but I just found a point with date %s" % (
                    date,
                    local_tz.normalize(existing_points[0].date)
                    )
                )
            return
        logger.info("Point does not exist, updating.")
        source = LocationSource()
        source.name = "Google Latitude Location at  %s" % local_tz.normalize(date)
        source.type = source_type
        source.data = data
        source.active = False
        source.save()

        point = LocationSnapshot()
        point.user = user
        point.location = Point(
                    data['data']['longitude'],
                    data['data']['latitude'],
                )
        point.source = source
        point.date = date
        point.save()

    def refresh_access_token(self, data):
        r = requests.post(
                'https://accounts.google.com/o/oauth2/token',
                data={
                    'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
                    'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                    'refresh_token': data['refresh_token'],
                    'grant_type': 'refresh_token'
                    },
                )
        logger.debug(r.text)
        response = json.loads(r.text)
        data['access_token'] = response['access_token']
        data['id_token'] = response['id_token']
        data['expiration_date'] = time.mktime(datetime.datetime.now().timetuple()) + response['expires_in']
        return data

    def get_current_location(self, data):
        r = requests.get(
                'https://www.googleapis.com/latitude/v1/currentLocation?granularity=best',
                headers={
                    'Authorization': 'Bearer ' + data['access_token']
                    }
                )
        logger.debug(r.text)
        response = json.loads(r.text)
        return response

