import datetime

from django.contrib.gis.geos import Point
from django.dispatch import receiver
from django.utils.timezone import utc

from location.models import (
    LocationSnapshot,
    LocationSource,
    LocationSourceType,
)
from location.signals import location_updated, watch_location
from location.tests.base import BaseTestCase


class SignalTest(BaseTestCase):
    def setUp(self):
        super(SignalTest, self).setUp()
        self.signal_receipts = []

        self.source_type, _ = LocationSourceType.objects.get_or_create(
            name='Arbitrary Source Type'
        )
        self.source = LocationSource.objects.create(
            name='Arbitrary Source',
            type=self.source_type,
            user=self.user,
            active=False,
        )
        self.snapshot = LocationSnapshot.objects.create(
            source=self.source,
            location=Point(
                10,
                10
            ),
            date=datetime.datetime.utcnow().replace(tzinfo=utc)
        )

    def test_watch_location_changed(self):
        @receiver(location_updated, dispatch_uid='signal_test_uid')
        def process_incoming_location(*args, **kwargs):
            self.signal_receipts.append({
                'args': args,
                'kwargs': kwargs,
            })

        with watch_location(self.user):
            LocationSnapshot.objects.create(
                source=self.source,
                location=Point(
                    10,
                    11
                ),
                date=datetime.datetime.utcnow().replace(tzinfo=utc)
            )

        self.assertTrue(
            len(self.signal_receipts) == 1
        )

    def test_watch_location_unchanged(self):
        @receiver(location_updated, dispatch_uid='signal_test_uid')
        def process_incoming_location(*args, **kwargs):
            self.signal_receipts.append({
                'args': args,
                'kwargs': kwargs,
            })

        with watch_location(self.user):
            pass

        self.assertTrue(
            len(self.signal_receipts) == 0
        )

    def test_watch_location_old(self):
        @receiver(location_updated, dispatch_uid='signal_test_uid')
        def process_incoming_location(*args, **kwargs):
            self.signal_receipts.append({
                'args': args,
                'kwargs': kwargs,
            })

        with watch_location(self.user):
            LocationSnapshot.objects.create(
                source=self.source,
                location=Point(
                    10,
                    11
                ),
                date=(
                    datetime.datetime.utcnow().replace(tzinfo=utc)
                    - datetime.timedelta(hours=1)
                )
            )

        self.assertTrue(
            len(self.signal_receipts) == 0
        )
