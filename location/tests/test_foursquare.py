import calendar
import datetime
import json

from django.contrib.gis.geos import Point
from django.utils.timezone import utc
from mock import MagicMock

from location import models
from location.tests.base import BaseTestCase
from location.consumers import foursquare


class FoursquareTest(BaseTestCase):
    def test_process_checkin(self):
        arbitrary_latitude = 60
        arbitrary_longitude = 32
        arbitrary_date = datetime.datetime(2013, 3, 2).replace(tzinfo=utc)
        checkin_data = {
            'type': 'checkin',
            'venue': {
                'location': {
                    'lat': arbitrary_latitude,
                    'lng': arbitrary_longitude,
                },
                'name': 'Test Location',
            },
            'createdAt': calendar.timegm(arbitrary_date.timetuple()),
            'timeZone': 'UTC'
        }

        foursquare.FoursquareConsumer.get_user = MagicMock()
        foursquare.FoursquareConsumer.get_user.return_value = self.user

        self.foursquare_consumer = foursquare.FoursquareConsumer(
            json.dumps(checkin_data)
        )
        self.foursquare_consumer.process_checkin()

        location = models.LocationSnapshot.objects.get()
        self.assertEqual(
            location.location,
            Point(arbitrary_longitude, arbitrary_latitude)
        )
        self.assertEqual(
            location.date,
            arbitrary_date,
        )
        self.assertIsNotNone(location.source)
