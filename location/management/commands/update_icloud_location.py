import datetime
import hashlib
import logging
import time

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
import pyicloud
import pyicloud.exceptions
import pytz

from location.models import (
    LocationSourceType,
    LocationSource,
    LocationSnapshot,
    CACHE_PREFIX
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


MIN_HORIZONTAL_ACCURACY = getattr(
    settings,
    'DJANGO_LOCATION_ICLOUD_MIN_HORIZONTAL_ACCURACY',
    20
) # Lower is better
MAX_WAIT_SECONDS = getattr(
    settings,
    'DJANGO_LOCATION_ICLOUD_MAX_LOCATION_WAIT_SECONDS',
    60
)
REQUEST_INTERVAL_SECONDS = getattr(
    settings,
    'DJANGO_LOCATION_ICLOUD_REQUEST_INTERVAL_SECONDS',
    5
)
FAILED_LOGIN_WAIT_SECONDS = getattr(
    settings,
    'DJANGO_LOCATION_ICLOUD_FAILED_LOGIN_WAIT_SECONDS',
    86400
)


class LocationUnavailableException(Exception):
    pass


class FailedLoginDelay(Exception):
    pass


class Command(BaseCommand):
    args = '<django.contrib.auth.models.User.username> <apple icloud username> <apple icloud password> <device id - defaults to first device>'
    help = 'Polls Apple\'s iCloud service for a device\'s location.'

    @transaction.commit_on_success
    def handle(self, *args, **kwargs):
        user = User.objects.get(username=args[0])
        icloud_username = args[1]
        icloud_password = args[2]
        try:
            device_id = args[3]
        except IndexError:
            device_id = 0

        blocking_key = self.get_cache_key(icloud_username, icloud_password)
        data = cache.get(
            blocking_key
        )
        if data and data > datetime.datetime.utcnow():
            raise FailedLoginDelay(
                'Previous login failed for this username and password '
                'delaying further attempts until %s UTC.' % data
            )

        try:
            location_data = self.get_location_data(
                icloud_username,
                icloud_password,
                device_id,
            )
            self.update_location(location_data, user)
        except pyicloud.exceptions.PyiCloudFailedLoginException:
            until = (
                datetime.datetime.utcnow()
                + datetime.timedelta(seconds=FAILED_LOGIN_WAIT_SECONDS)
            )
            cache.set(
                blocking_key,
                until,
                FAILED_LOGIN_WAIT_SECONDS
            )
            logger.warning(
                'Encountered a login failure while attempting to connect '
                'to iCloud.  Delaying further accesses of iCloud for this '
                'username and password until %s UTC.' % until
            )

    def get_cache_key(self, icloud_username, icloud_password):
        key = icloud_username + ':' + hashlib.sha256(
            icloud_username + icloud_password
        ).hexdigest()
        return CACHE_PREFIX + ':' + key

    def location_is_accurate(self, data):
        if not data:
            logger.info("No location data available")
            return False
        if not data['locationFinished']:
            logger.info("Location not ready")
            return False
        if data['horizontalAccuracy'] > MIN_HORIZONTAL_ACCURACY:
            logger.info(
                "Horizontal Accuracy insufficient (> %s)" % (
                    MIN_HORIZONTAL_ACCURACY
                )
            )
            return False
        if data['isInaccurate']:
            logger.info("Location marked as inaccurate.")
            return False
        if data['isOld']:
            logger.info("Location explicitly marked as inaccurate.")
            return False
        return True

    def get_location_data(self, icloud_username, icloud_password, device_id):
        api = pyicloud.PyiCloudService(icloud_username, icloud_password)

        started = time.time()
        while time.time() - started < MAX_WAIT_SECONDS:
            data = api.devices[device_id].location()
            logger.debug(data)
            if self.location_is_accurate(data):
                logger.info("Valid location acquired.")
                return data
            logger.info("Waiting for %s seconds." % REQUEST_INTERVAL_SECONDS)
            time.sleep(REQUEST_INTERVAL_SECONDS)
        raise LocationUnavailableException(
            'Unable to acquire location of device %s within %s seconds' % (
                api.devices[device_id],
                MAX_WAIT_SECONDS
            )
        )

    def update_location(self, data, user):
        (source_type, created) = LocationSourceType.objects.get_or_create(name='Apple iCloud')

        local_tz = pytz.timezone('US/Pacific-New')
        date = datetime.datetime.fromtimestamp(
            float(data['timeStamp']) / 1000,
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

        source = LocationSource.objects.create(
            name='Apple iCloud location at %s' % local_tz.normalize(date),
            type=source_type,
            active=False
        )
        source.data = data
        source.save()

        point = LocationSnapshot.objects.create(
            user=user,
            location=Point(
                data['longitude'],
                data['latitude'],
            ),
            source=source,
            date=date
        )
