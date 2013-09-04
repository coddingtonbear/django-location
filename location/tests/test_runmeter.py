import datetime
import json
import os.path

from django.contrib.gis.geos import Point
from django.utils.timezone import utc
from django_mailbox.models import Mailbox, Message
from lxml import objectify
from mock import MagicMock

from location import models
from location.tests.base import BaseTestCase
from location.consumers.runmeter import RunmeterConsumer


class RunmeterTest(BaseTestCase):
    def setUp(self):
        super(RunmeterTest, self).setUp()
        self.arbitrary_email = 'phlogiston@becker.net'
        self.settings = models.LocationConsumerSettings.objects.create(
            user=self.user,
            runmeter_enabled=True,
            runmeter_email=self.arbitrary_email,
        )
        self.mailbox = Mailbox.objects.create(
            name='My Mailbox',
        )
        self.source_type = RunmeterConsumer.get_source_type()

    def _get_sample_document(self):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'files/sample_cycle.kml',
        )
        with open(file_path, 'r') as incoming:
            return objectify.fromstring(incoming.read())

    def test_process_message(self):
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
        RunmeterConsumer.get_import_url_from_message_body = MagicMock(
            return_value=arbitrary_url
        )
        RunmeterConsumer.get_source_from_user_and_url = MagicMock(
            return_value=arbitrary_source
        )
        RunmeterConsumer.message_indicates_finish = MagicMock(
            return_value=False
        )
        RunmeterConsumer.process = MagicMock()

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

    def test_process(self):
        pass

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
        arbitrary_source.created=datetime.datetime(1970, 1, 1).replace(tzinfo=utc)
        arbitrary_source.save()

        actual_source = RunmeterConsumer.get_source_from_user_and_url(
            self.user,
            arbitrary_url,
        )

        self.assertNotEqual(
            arbitrary_source.pk,
            actual_source.pk,
        )
