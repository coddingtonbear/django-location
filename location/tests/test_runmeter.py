import datetime
import json
import os.path

from django.contrib.gis.geos import Point
from django.utils.timezone import utc
from django_mailbox.models import Mailbox, Message
from django_mailbox.signals import message_received
from lxml import objectify
from mock import MagicMock, patch

from location import models
from location.tests.base import BaseTestCase
from location.consumers.runmeter import RunmeterConsumer


class RunmeterTest(BaseTestCase):
    def setUp(self):
        super(RunmeterTest, self).setUp()
        self.arbitrary_email = 'phlogiston@becker.net'
        self.arbitrary_mailbox = 'Runmeter Mailbox'
        self.settings = models.LocationConsumerSettings.objects.create(
            user=self.user,
            runmeter_enabled=True,
            runmeter_email=self.arbitrary_email,
        )
        self.mailbox = Mailbox.objects.create(
            name=self.arbitrary_mailbox,
        )
        self.source_type = RunmeterConsumer.get_source_type()
        models.SETTINGS['runmeter_mailbox'] = self.arbitrary_mailbox

    def _get_sample_document(self):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'files/sample_cycle.kml',
        )
        with open(file_path, 'r') as incoming:
            return objectify.fromstring(incoming.read())

    @patch.object(RunmeterConsumer, 'get_import_url_from_message_body')
    @patch.object(RunmeterConsumer, 'get_source_from_user_and_url')
    @patch.object(RunmeterConsumer, 'message_indicates_finish')
    @patch.object(RunmeterConsumer, 'process')
    def test_process_message(
        self, process, message_indicates_finish,
        get_source_from_user_and_url, get_import_url_from_message_body
    ):
        arbitrary_body = 'I am the very model of a modern major general'
        arbitrary_url = 'http://go.com/'
        arbitrary_source = models.LocationSource.objects.create(
            name='Whatnot',
            user=self.user,
            type=self.source_type,
        )
        ok_message = Message.objects.create(
            mailbox=self.mailbox,
            subject='Whatever',
            from_header=self.arbitrary_email,
            body=arbitrary_body,
        )
        get_import_url_from_message_body.return_value = (
            arbitrary_url
        )
        get_source_from_user_and_url.return_value = (
            arbitrary_source
        )
        message_indicates_finish.return_value = (
            False
        )

        RunmeterConsumer.process_message(ok_message)

        RunmeterConsumer.get_import_url_from_message_body.assert_called_with(
            arbitrary_body,
        )
        RunmeterConsumer.get_source_from_user_and_url.assert_called_with(
            self.settings.user,
            arbitrary_url,
        )

    def test_get_route_name(self):
        document = self._get_sample_document()
        consumer = RunmeterConsumer(None)
        actual_value = consumer.get_route_name(document)
        expected_value = 'Cycle'

        self.assertEqual(
            actual_value,
            expected_value,
        )

    def test_get_start_time(self):
        document = self._get_sample_document()
        consumer = RunmeterConsumer(None)
        actual_value = consumer.get_start_time(document)
        expected_value = datetime.datetime(2013, 9, 6, 0, 51, 29).replace(
            tzinfo=utc
        )

        self.assertEqual(
            actual_value,
            expected_value,
        )

    def test_get_points(self):
        arbitrary_time = datetime.datetime.utcnow().replace(tzinfo=utc)
        document = self._get_sample_document()
        consumer = RunmeterConsumer(None)
        actual_value = consumer.get_points(document, arbitrary_time)

        with open(
            os.path.join(
                os.path.dirname(__file__),
                'files/expected_points.json',
            )
        ) as incoming:
            expected_value = json.loads(incoming.read())

        self.assertEqual(
            actual_value,
            expected_value,
        )

    def test_process_new_source(self):
        arbitrary_url = 'http://www.go.com/101'
        arbitrary_route_name = 'Something'
        arbitrary_source = models.LocationSource.objects.create(
            name='Whatnot',
            user=self.user,
            type=self.source_type,
            active=True,
            data={
                'url': arbitrary_url,
                'known_points': {},
            }
        )
        arbitrary_document = MagicMock()
        arbitrary_time = datetime.datetime.utcnow().replace(
            tzinfo=utc
        )
        arbitrary_points = [
            {'lat': -122, 'lng': 45, 'key': 'alpha', 'time': 1},
            {'lat': -123, 'lng': 44, 'key': 'beta', 'time': 2}
        ]

        consumer = RunmeterConsumer(arbitrary_source)
        consumer._get_document = MagicMock(
            return_value=arbitrary_document
        )
        consumer.get_start_time = MagicMock(
            return_value=arbitrary_time
        )
        consumer.get_route_name = MagicMock(
            return_value=arbitrary_route_name
        )
        consumer.get_points = MagicMock(
            return_value=arbitrary_points
        )
        consumer.is_active = MagicMock(
            return_value=False
        )

        consumer.process()

        consumer._get_document.assert_called_with(arbitrary_url)
        consumer.get_start_time.assert_called_with(arbitrary_document)
        consumer.get_route_name.assert_called_with(arbitrary_document)
        consumer.get_points.assert_called_with(arbitrary_document)

        actual_points = models.LocationSnapshot.objects.order_by('date')
        self.assertEqual(actual_points.count(), 2)

        first_assertions = {
            'date': arbitrary_time + datetime.timedelta(seconds=1),
            'source': arbitrary_source,
            'location': Point(-122, 45)
        }
        for k, v in first_assertions.items():
            self.assertEqual(getattr(actual_points[0], k), v)

        second_assertions = {
            'date': arbitrary_time + datetime.timedelta(seconds=2),
            'source': arbitrary_source,
            'location': Point(-123, 44)
        }
        for k, v in second_assertions.items():
            self.assertEqual(getattr(actual_points[1], k), v)

        self.assertFalse(
            models.LocationSource.objects.get(pk=arbitrary_source.pk).active
        )

    def test_process_existing_source(self):
        arbitrary_url = 'http://www.go.com/101'
        arbitrary_route_name = 'Something'
        arbitrary_source = models.LocationSource.objects.create(
            name='Whatnot',
            user=self.user,
            type=self.source_type,
            active=True,
            data={
                'url': arbitrary_url,
                'known_points': {
                    'alpha': 'arbitrary_value'
                },
            }
        )
        arbitrary_document = MagicMock()
        arbitrary_time = datetime.datetime.utcnow().replace(
            tzinfo=utc
        )
        arbitrary_points = [
            {'lat': -122, 'lng': 45, 'key': 'alpha', 'time': 1},
            {'lat': -123, 'lng': 44, 'key': 'beta', 'time': 2}
        ]

        consumer = RunmeterConsumer(arbitrary_source)
        consumer._get_document = MagicMock(
            return_value=arbitrary_document
        )
        consumer.get_start_time = MagicMock(
            return_value=arbitrary_time
        )
        consumer.get_route_name = MagicMock(
            return_value=arbitrary_route_name
        )
        consumer.get_points = MagicMock(
            return_value=arbitrary_points
        )
        consumer.is_active = MagicMock(
            return_value=True
        )

        consumer.process()

        consumer._get_document.assert_called_with(arbitrary_url)
        consumer.get_start_time.assert_called_with(arbitrary_document)
        consumer.get_route_name.assert_called_with(arbitrary_document)
        consumer.get_points.assert_called_with(arbitrary_document)

        actual_points = models.LocationSnapshot.objects.order_by('date')
        self.assertEqual(actual_points.count(), 1)

        assertions = {
            'date': arbitrary_time + datetime.timedelta(seconds=2),
            'source': arbitrary_source,
            'location': Point(-123, 44)
        }
        for k, v in assertions.items():
            self.assertEqual(getattr(actual_points[0], k), v)

        self.assertTrue(
            models.LocationSource.objects.get(pk=arbitrary_source.pk).active
        )

    def test_get_source_from_user_and_url_new(self):
        arbitrary_url = 'http://www.go.com/100'

        actual_source = RunmeterConsumer.get_source_from_user_and_url(
            self.user,
            arbitrary_url,
        )

        assertions = {
            'type': self.source_type,
            'data': {
                'url': arbitrary_url,
                'known_points': {},
            },
            'active': True
        }

        for k, v in assertions.items():
            self.assertEqual(getattr(actual_source, k), v)

    def test_get_source_from_user_and_url_existing(self):
        arbitrary_url = 'http://www.go.com/100'

        arbitrary_source = models.LocationSource.objects.create(
            name='Whatnot',
            user=self.user,
            type=self.source_type,
            data={
                'url': arbitrary_url,
                'known_points': {},
            }
        )

        actual_source = RunmeterConsumer.get_source_from_user_and_url(
            self.user,
            arbitrary_url,
        )

        self.assertEqual(
            arbitrary_source.pk,
            actual_source.pk,
        )

    def test_get_source_from_user_and_url_existing_too_old(self):
        arbitrary_url = 'http://www.go.com/100'

        arbitrary_source = models.LocationSource.objects.create(
            name='Whatnot',
            user=self.user,
            type=self.source_type,
            data={
                'url': arbitrary_url,
                'known_points': {},
            },
        )
        arbitrary_source.created = datetime.datetime(1970, 1, 1).replace(
            tzinfo=utc
        )
        arbitrary_source.save()

        actual_source = RunmeterConsumer.get_source_from_user_and_url(
            self.user,
            arbitrary_url,
        )

        self.assertNotEqual(
            arbitrary_source.pk,
            actual_source.pk,
        )

    @patch.object(RunmeterConsumer, 'process_message')
    def test_signal_receipt(self, process_message):
        arbitrary_body = 'OK'
        ok_message = Message.objects.create(
            mailbox=self.mailbox,
            subject='Whatever',
            from_header=self.arbitrary_email,
            body=arbitrary_body,
        )
        message_received.send(
            sender=self,
            message=ok_message
        )

        process_message.assert_called_with(ok_message)
