import datetime
import logging
import re

from django.contrib.gis.geos import Point
from django.utils.timezone import utc
from django.db.models import Max
from lxml import objectify
import requests

from location.models import (
    LocationConsumerSettings,
    LocationSnapshot,
    LocationSource,
    LocationSourceType
)


logger = logging.getLogger(__name__)


class RunmeterConsumer(object):
    NAMESPACES = {
        'kml': 'http://www.opengis.net/kml/2.2',
        'abvio': 'http://www.abvio.com/xmlschemas/1'
    }

    def __init__(self, source):
        self.source = source

    @classmethod
    def periodic(cls):
        cls.process_active_sources()

    @classmethod
    def process_message(cls, message):
        settings = LocationConsumerSettings.objects.get(
            runmeter_enabled=True,
            runmeter_email=message.from_address[0],
        )

        url = cls.get_import_url_from_message_body(message.text)
        source = cls.get_source_from_user_and_url(settings.user, url)

        if cls.message_indicates_finish(message.text):
            source.active = False

        instance = RunmeterConsumer(source)
        instance.process()

        message.read = datetime.datetime.utcnow().replace(tzinfo=utc)
        message.save()

        return instance

    @classmethod
    def process_active_sources(cls):
        source_type = cls.get_source_type()
        sources = LocationSource.objects.filter(
            type=source_type,
            active=True,
        )
        for source in sources:
            logger.debug(
                'Found active source %s.', source
            )
            instance = RunmeterConsumer(source)
            instance.process()

    def process(self):
        logger.info('Processing source %s.', self.source)
        document = self._get_document(self.source.data['url'])

        base_time = self.get_start_time(document)
        route_name = self.get_route_name(document)

        for raw_point in self.get_points(document):
            key_name = raw_point['key']
            if isinstance(self.source.data['known_points'], list):
                self.source.data['known_points'] = {}
            if key_name not in self.source.data['known_points']:
                point = self._get_processed_point(raw_point, base_time)
                logger.debug(
                    'Creating point %s,%s at %s.',
                    point['lat'],
                    point['lng'],
                    point['date'],
                )
                LocationSnapshot.objects.create(
                    source=self.source,
                    location=point['point'],
                    date=point['date'],
                )
                self.source.data['known_points'][key_name] = raw_point
            else:
                logger.debug(
                    'Point %s,%s already stored.',
                    raw_point['lat'],
                    raw_point['lng'],
                )

        if route_name:
            self.source.name = '%s (%s)' % (
                route_name if route_name else 'AdHoc',
                self.source.data['url']
            )
        if self.source.active:
            self.source.active = self.is_active()
            if not self.source.active:
                logger.debug('Source has expired; marked inactive.')
        self.source.save()

    def get_route_name(self, document):
        values = document.xpath(
            '//abvio:routeName',
            namespaces=self.NAMESPACES
        )
        if values:
            return values[0].text
        values = document.xpath(
            '//abvio:activityName',
            namespaces=self.NAMESPACES
        )
        if values:
            return values[0].text
        return None

    def get_start_time(self, document):
        start_string = document.xpath(
            '//abvio:startTime',
            namespaces=self.NAMESPACES
        )[0].text

        return datetime.datetime.strptime(
            start_string[0:19],
            "%Y-%m-%d %H:%M:%S"
        ).replace(
            tzinfo=utc
        )

    def get_points(self, document, base_time):
        points = []
        coordinate_table = document.xpath(
            '//abvio:coordinateTable',
            namespaces=self.NAMESPACES
        )[0].text.split('\n')
        for coordinate_row in coordinate_table:
            if coordinate_row:
                cols = coordinate_row.split(',')
                points.append({
                    'key': coordinate_row,
                    'time': float(cols[0]),
                    'lng': float(cols[1]),
                    'lat': float(cols[2]),
                })
        return points

    def _get_processed_point(self, point, base_time):
        point = point.copy()
        point['point'] = Point(
            point['lat'],
            point['lng'],
        )
        point['date'] = base_time + datetime.timedelta(
            seconds=point['time']
        )
        return point

    def _get_document(self, url):
        return objectify.fromstring(
            requests.get(url).content
        )

    @classmethod
    def get_source_type(cls):
        source_type, _ = LocationSourceType.objects.get_or_create(
            name='Runmeter'
        )
        return source_type

    @classmethod
    def get_source_from_user_and_url(cls, user, url, **additional_filters):
        source_type = cls.get_source_type()
        source = None
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        minimum_time = now - datetime.timedelta(days=1)
        for potential_source in LocationSource.objects.filter(
            created__gt=minimum_time,
            user=user,
            type=source_type,
            **additional_filters
        ):
            data = potential_source.data
            if 'url' in data.keys() and data['url'] == url:
                source = potential_source
                logger.info("Found existing source with ID %s.", source.id)
                break
        if not source:
            source = LocationSource()
            source.type = source_type
            source.name = "Runmeter Route at %s" % datetime.datetime.now()
            source.data = {
                'url': url,
                'known_points': {}
            }
            source.active = True
            source.save()
            logger.info("Created new source with ID %s.", source.id)
        return source

    def is_active(self):
        max_date = self.source.points.aggregate(avg=Max('date'))['avg']
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        logger.debug("Max Date %s", max_date)
        logger.debug("Now %s", now)
        if max_date and now - max_date > datetime.timedelta(minutes=60):
            return False
        return True

    @classmethod
    def message_indicates_finish(self, body):
        if re.search('Finished [A-Za-z0-9-_]+:', body):
            return True
        return False

    @classmethod
    def get_import_url_from_message_body(self, body):
        matches = re.search(r"Import Link: (.*)", body)
        if not matches:
            matches = re.search(r"Import URL: (.*)", body)
            if not matches:
                return None
        return matches.groups()[0].strip()
