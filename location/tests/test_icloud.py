import calendar
import datetime

from django.contrib.gis.geos import Point
from django.utils.timezone import utc
import pyicloud

from location import models
from location.tests.base import BaseTestCase
from location.consumers import icloud


class iCloudTest(BaseTestCase):
    def setUp(self):
        super(iCloudTest, self).setUp()
        self.arbitrary_username = 'arbitrary_username'
        self.arbitrary_password = 'arbitrary_password'
        self.arbitrary_device_id = 'arbitrary_device_id'
        self.user_settings = models.LocationConsumerSettings.objects.create(
            user=self.user,
            icloud_enabled=True,
            icloud_username=self.arbitrary_username,
            icloud_password=self.arbitrary_password,
            icloud_device_id=self.arbitrary_device_id,
            icloud_timezone='UTC'
        )
        icloud.SETTINGS['icloud']['max_wait_seconds'] = 0.5
        icloud.SETTINGS['icloud']['request_interval_seconds'] = 0.1
        self.icloud_consumer = icloud.iCloudConsumer(self.user_settings)

    def test_periodic(self):
        pass

    def test_get_location_data_unknown_device_id(self):
        self.mimic.stub_out_with_mock(pyicloud.PyiCloudService, '__init__')
        pyicloud.PyiCloudService.__init__(
            self.arbitrary_username,
            self.arbitrary_password,
        )
        pyicloud.PyiCloudService.devices = {}

        self.mimic.replay_all()

        with self.assertRaises(icloud.UnknownDeviceException):
            self.icloud_consumer.get_location_data()

    def test_get_location_data(self):
        arbitrary_location_data = {
            'somewhere': 'around',
            'here': True
        }
        self.mimic.stub_out_with_mock(pyicloud.PyiCloudService, '__init__')
        pyicloud.PyiCloudService.__init__(
            self.arbitrary_username,
            self.arbitrary_password,
        )
        mock_device = self.mimic.CreateMockAnything()
        pyicloud.PyiCloudService.devices = {}
        pyicloud.PyiCloudService.devices[self.arbitrary_device_id] = (
            mock_device
        )
        self.mimic.stub_out_with_mock(
            self.icloud_consumer,
            'data_is_accurate'
        )
        self.icloud_consumer.data_is_accurate(
            arbitrary_location_data
        ).and_return(True)

        mock_device.location().and_return(arbitrary_location_data)

        self.mimic.replay_all()

        actual_data = self.icloud_consumer.get_location_data()

        self.assertEqual(
            actual_data,
            arbitrary_location_data
        )

    def test_get_location_data_inaccurate(self):
        arbitrary_location_data = {
            'somewhere': 'around',
            'here': True
        }
        self.mimic.stub_out_with_mock(pyicloud.PyiCloudService, '__init__')
        pyicloud.PyiCloudService.__init__(
            self.arbitrary_username,
            self.arbitrary_password,
        )
        mock_device = self.mimic.CreateMockAnything()
        pyicloud.PyiCloudService.devices = {}
        pyicloud.PyiCloudService.devices[self.arbitrary_device_id] = (
            mock_device
        )
        mock_device.location().multiple_times().and_return(
            arbitrary_location_data
        )
        self.mimic.stub_out_with_mock(
            self.icloud_consumer,
            'data_is_accurate'
        )
        self.icloud_consumer.data_is_accurate(
            arbitrary_location_data
        ).multiple_times().and_return(False)

        self.mimic.replay_all()

        with self.assertRaises(icloud.LocationUnavailableException):
            self.icloud_consumer.get_location_data()

    def test_data_is_accurate(self):
        accurate_data = {
            'locationFinished': True,
            'isInaccurate': False,
            'isOld': False,
            'horizontalAccuracy': 1,
        }

        actual_result = self.icloud_consumer.data_is_accurate(accurate_data)

        self.assertTrue(
            actual_result,
        )

    def test_location_not_finished(self):
        failure_data = {
            'locationFinished': False,
            'isInaccurate': False,
            'isOld': False,
            'horizontalAccuracy': 1,
        }

        actual_result = self.icloud_consumer.data_is_accurate(failure_data)

        self.assertFalse(
            actual_result,
        )

    def test_location_inaccurate(self):
        failure_data = {
            'locationFinished': True,
            'isInaccurate': True,
            'isOld': False,
            'horizontalAccuracy': 1,
        }

        actual_result = self.icloud_consumer.data_is_accurate(failure_data)

        self.assertFalse(
            actual_result,
        )

    def test_location_is_old(self):
        failure_data = {
            'locationFinished': True,
            'isInaccurate': False,
            'isOld': True,
            'horizontalAccuracy': 1,
        }

        actual_result = self.icloud_consumer.data_is_accurate(failure_data)

        self.assertFalse(
            actual_result,
        )

    def test_insufficient_horizontal_accuracy(self):
        failure_data = {
            'locationFinished': True,
            'isInaccurate': False,
            'isOld': True,
            'horizontalAccuracy': (
                icloud.SETTINGS['icloud']['min_horizontal_accuracy'] * 2
            ),
        }

        actual_result = self.icloud_consumer.data_is_accurate(failure_data)

        self.assertFalse(
            actual_result,
        )

    def test_update_location(self):
        arbitrary_time = datetime.datetime(2013, 3, 2).replace(tzinfo=utc)
        arbitrary_latitude = 100
        arbitrary_longitude = 120
        mock_location_data = {
            'timeStamp': calendar.timegm(arbitrary_time.timetuple()) * 1000,
            'longitude': arbitrary_longitude,
            'latitude': arbitrary_latitude,
        }

        self.mimic.stub_out_with_mock(
            self.icloud_consumer, 'get_location_data'
        )
        self.icloud_consumer.get_location_data().and_return(mock_location_data)

        self.mimic.replay_all()

        self.icloud_consumer.update_location()

        snapshot = models.LocationSnapshot.objects.get()
        self.assertIsNotNone(snapshot.source)
        self.assertEqual(
            snapshot.location,
            Point(arbitrary_longitude, arbitrary_latitude)
        )
        self.assertEqual(
            snapshot.date,
            arbitrary_time,
        )
