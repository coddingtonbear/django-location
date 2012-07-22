import datetime
import logging
import urllib2
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from django.utils.timezone import utc
from lxml import objectify

from location.models import LocationSource, LocationSourceType, LocationSnapshot
from django_mailbox.models import Message

logger = logging.getLogger('location.management.commands.check_incoming_runmeter')
logging.basicConfig(level=logging.INFO)

MINIMUM_INTERVAL_SECONDS = getattr(settings, 'RUNMETER_MINIMAL_INTERVAL_SECONDS', 30)

class Command(BaseCommand):
    args = '<django_mailbox.models.Mailbox.name> <django.contrib.auth.models.User.username>' 
    help = 'Imports start and end e-mail messages sent by Runmeter (http://www.abvio.com/runmeter/) '\
            + 'delivered to a mailbox watched by django_mailbox, creating location points for the '\
            + 'username specified.'
    namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'abvio': 'http://www.abvio.com/xmlschemas/1'
            }

    @transaction.commit_on_success
    def handle(self, *args, **options):
        self.user = User.objects.get(username=args[1])
        mailbox_name = args[0]
        messages = Message.objects.filter(
                    mailbox__name = mailbox_name
                    ).order_by('received')
        for message in messages:
            logger.info("Received message %s" % message)
            url = self.get_import_url(message)
            logger.debug("Import URL %s" % url)
            source = self.get_source(url)
            if self.is_finish_email(message):
                logger.info("Is finishing e-mail.")
                source.active = False
            self.process_source(source)
            message.delete()
            logger.debug("Deleted.")
        
        for ongoing_source in LocationSource.objects.filter(active=True):
            self.process_source(ongoing_source)

    def process_source(self, source):
        logger.info("Processing source %s" % source)
        document = self.get_document(source.data['url'])
        start_time = self.get_start_time(document)
        points = self.get_points(document)
        route_name = self.get_route_name(document)

        max_date = LocationSnapshot.objects\
                .filter(source=source)\
                .aggregate(max_date=Max('date'))['max_date']
        for key_name, data_point in points.items():
            if key_name not in source.data['known_points'].keys():
                logger.debug("%s not in %s" % (
                        key_name,
                        source.data['known_points'].keys()
                    ))
                logger.debug("Creating point %s,%s" % (
                        data_point['lat'],
                        data_point['lng'],
                    ))
                point_date = start_time + datetime.timedelta(
                            seconds = data_point['time']
                            )
                if max_date and max_date + datetime.timedelta(seconds=MINIMUM_INTERVAL_SECONDS) < point_date:
                    point = LocationSnapshot()
                    point.user = self.user
                    point.location = Point(
                                data_point['lat'],
                                data_point['lng']
                                )
                    point.source = source
                    point.date = point_date
                    point.save()
                    max_date = point_date
                source.data['known_points'][key_name] = data_point
            else:
                logger.debug("Point already exists")
        if route_name:
            source.name = "%s (%s)" % (
                    route_name if route_name else 'AdHoc',
                    source.data['url']
                    )
        if source.active:
            source.active = self.get_activity_status(document, source)
        source.save()

    def is_finish_email(self, message):
        if re.search('Finished [A-Za-z0-9-_]+:', message.body):
            return True
        return False

    def get_activity_status(self, document, source):
        max_date = source.points.aggregate(avg=Max('date'))['avg']
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        logger.debug("Max Date %s" % max_date)
        logger.debug("Now %s" % now)
        if max_date and now - max_date > datetime.timedelta(minutes = 60):
            return False
        return True

    def get_source(self, url):
        (source_type, created) = LocationSourceType.objects.get_or_create(name='Runmeter')
        source = None
        for potential_source in LocationSource.objects.filter(
                created__gt = datetime.datetime.now().replace(tzinfo=utc) - datetime.timedelta(days=1),
                active=True
                ):
            data = potential_source.data
            if 'url' in data.keys() and data['url'] == url:
                source = potential_source
                logger.info("Found existing source")
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
            logger.info("Creating new source")
        return source

    def get_route_name(self, document):
        values = document.xpath('//abvio:routeName', namespaces=self.namespaces)
        if values:
            return values[0].text
        values = document.xpath('//abvio:activityName', namespaces=self.namespaces)
        if values:
            return values[0].text
        return None

    def get_start_time(self, document):
        start_string = document.xpath('//abvio:startTime', namespaces=self.namespaces)[0].text

        return datetime.datetime.strptime(start_string[0:19], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=utc
                )

    def get_points(self, document):
        points = {}
        coordinate_table = document.xpath('//abvio:coordinateTable', namespaces=self.namespaces)[0].text.split('\n')
        for coordinate_row in coordinate_table:
            if coordinate_row:
                cols = coordinate_row.split(',')
                points[coordinate_row] = {
                        'time': float(cols[0]),
                        'lng': float(cols[1]),
                        'lat': float(cols[2]),
                        }
        return points

    def get_document(self, url):
        return objectify.fromstring(
                urllib2.urlopen(url).read()
                )

    def get_import_url(self, message):
        matches = re.search(r"Import URL: (.*)", message.body)
        if not matches:
            return None
        return matches.groups()[0].strip()
