import datetime
import logging
import time

from django.contrib.gis.geos import Point
import pyicloud
import pytz

from location.models import (
    LocationConsumerSettings,
    LocationSnapshot,
    LocationSource,
    LocationSourceType
)
from location.settings import SETTINGS


logger = logging.getLogger(__name__)


class LocationUnavailableException(Exception):
    pass


class UnknownDeviceException(Exception):
    pass


class iCloudConsumer(object):
    def __init__(self, user_settings):
        self.user_settings = user_settings

    @classmethod
    def periodic(cls):
        users = cls.get_icloud_enabled_settings()
        for user_settings in users:
            instance = cls(user_settings)
            try:
                instance.update_location()
            except pyicloud.exceptions.PyiCloudFailedLoginException:
                logger.exception(
                    'Unable to log-in to iCloud with the provided credentials '
                    '; disabling icloud for %s',
                    user_settings,
                )
                cls.disable_icloud(
                    user_settings,
                    "Unable to login to iCloud account '%s' using provided "
                    "credentials." % (
                        user_settings.icloud_device_id,
                        user_settings.icloud_username,
                    )
                )
            except UnknownDeviceException:
                logger.exception(
                    'Unable to find device on the account using the provided '
                    'credentials',
                    user_settings,
                )
                cls.disable_icloud(
                    user_settings,
                    "Unable to find device '%s' on iCloud account '%s'." % (
                        user_settings.icloud_device_id,
                        user_settings.icloud_username,
                    )
                )
            except LocationUnavailableException as e:
                logger.warning(
                    'Location currently unavailable for consumer settings %s',
                    instance,
                )
            except Exception as e:
                logger.exception(
                    'Unable to gather iCloud location for location consumer'
                    'settings %s: %s',
                    instance,
                    e

                )

    @classmethod
    def disable_icloud(cls, user_settings, message=None):
        user_settings.icloud_enabled = False
        user_settings.save()
        if message is not None:
            user_settings.user.email_user(
                'iCloud location consumption disabled',
                message
            )

    @classmethod
    def get_icloud_enabled_settings(cls):
        return LocationConsumerSettings.objects.filter(
            icloud_enabled=True
        )

    def get_location_data(self):
        api = pyicloud.PyiCloudService(
            self.user_settings.icloud_username,
            self.user_settings.icloud_password,
        )

        started = time.time()
        while time.time() - started < SETTINGS['icloud']['max_wait_seconds']:
            try:
                device = api.devices[self.user_settings.icloud_device_id]
            except KeyError:
                raise UnknownDeviceException(
                    'Device %s not found.' % (
                        self.user_settings.icloud_device_id,
                    )
                )

            data = device.location()

            logger.debug(
                'Gathered data %s from device %s.',
                data,
                self.user_settings.icloud_device_id,
            )
            if self.data_is_accurate(data):
                return data
            time.sleep(SETTINGS['icloud']['request_interval_seconds'])

        raise LocationUnavailableException(
            'Unable to acquire location of device %s within %s seconds',
            api.devices[self.user_settings.icloud_device_id],
            SETTINGS['icloud']['max_wait_seconds'],
        )

    def data_is_accurate(self, data):
        if not data:
            logger.info("No location data available.")
            return False
        elif not data['locationFinished']:
            logger.info("Location not ready.")
            return False
        elif data['isInaccurate']:
            logger.info('Location marked as inaccurate')
            return False
        elif data['isOld']:
            logger.info('Location explicitly marked as old')
            return False
        elif (
            data['horizontalAccuracy'] > (
                SETTINGS['icloud']['min_horizontal_accuracy']
            )
        ):
            logger.info(
                'Horizontal accuracy insufficient (%s > %s)',
                data['horizontalAccuracy'],
                SETTINGS['icloud']['min_horizontal_accuracy']
            )
            return False
        return True

    def update_location(self):
        source_type = self.get_source_type()
        data = self.get_location_data()

        local_tz = pytz.timezone(self.user_settings.icloud_timezone)

        date = datetime.datetime.fromtimestamp(
            float(data['timeStamp']) / 1000,
            local_tz
        )

        if LocationSnapshot.objects.filter(
            date__gt=date - datetime.timedelta(minutes=1),
            source__type=source_type,
            source__user=self.user_settings.user,
        ).exists():
            logger.info(
                'Found another sample from within the last minute; skipping '
                'gathered icloud location'
            )
            return

        source = LocationSource.objects.create(
            name='Apple iCloud location at %s' % date,
            type=source_type,
            user=self.user_settings.user,
            active=False,
        )
        return LocationSnapshot.objects.create(
            source=source,
            location=Point(
                data['longitude'],
                data['latitude'],
            ),
            date=date,
        )

    @classmethod
    def get_source_type(cls):
        source_type, _ = LocationSourceType.objects.get_or_create(
            name='Apple iCloud'
        )
        return source_type
