import datetime
import json

from django.contrib.gis.geos import Point
import pytz
from social_auth.models import UserSocialAuth

from location.models import (
    LocationSnapshot,
    LocationSource,
    LocationSourceType
)
from location.signals import watch_location


class FoursquareConsumer(object):
    def __init__(self, data):
        self.data = json.loads(data)

    def process_checkin(self):
        if self.data['type'] == 'checkin':
            user = self.get_user()
            source = LocationSource.objects.create(
                name=self.data['venue']['name'],
                user=user,
                type=self.get_source_type(),
                data=self.data
            )

            with watch_location(user):
                return LocationSnapshot.objects.create(
                    location=Point(
                        self.data['venue']['location']['lng'],
                        self.data['venue']['location']['lat'],
                    ),
                    date=(
                        datetime.datetime.fromtimestamp(
                            self.data['createdAt'],
                            pytz.timezone(self.data['timeZone']),
                        )
                    ),
                    source=source,
                )
        return None

    def get_user(self):
        return UserSocialAuth.objects.get(
            uid=self.data['user']['id'],
            provider='foursquare',
        ).user

    @classmethod
    def get_source_type(cls):
        source_type, _ = LocationSourceType.objects.get_or_create(
            name='Foursquare Check-in'
        )
        return source_type
