import datetime
import logging
import urllib2
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max, Min
from django.utils.timezone import utc
from lxml import objectify
from optparse import make_option

from location.models import LocationSource, LocationSourceType, LocationSnapshot
from django_mailbox.models import Message

logger = logging.getLogger('location.management.commands.check_incoming_runmeter')

MINIMUM_INTERVAL_SECONDS = getattr(settings, 'RUNMETER_MINIMAL_INTERVAL_SECONDS', 15)

class Command(BaseCommand):
    args = '<django_mailbox.models.Mailbox.name> <django.contrib.auth.models.User.username>' 
    help = 'Imports start and end e-mail messages sent by Runmeter (http://www.abvio.com/runmeter/) '\
            + 'delivered to a mailbox watched by django_mailbox, creating location points for the '\
            + 'username specified.'
    namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'abvio': 'http://www.abvio.com/xmlschemas/1'
            }
    option_list = BaseCommand.option_list + (
        make_option('--debug',
            action='store_true',
            dest='debug',
            default=False,
            help='Display detailed logging information.'),
        make_option('--confirm',
            action='store_true',
            dest='confirm',
            default=False,
            help=(
                'Require manual confirmation before processing and marking '
                'messages as read.'
                ),
            )
        )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        if options['debug'] or options['confirm']:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        self.user = User.objects.get(username=args[1])
        mailbox_name = args[0]
        messages = Message.unread_messages.filter(
                    mailbox__name = mailbox_name
                ).order_by('processed')
        for message in messages:
            logger.info("Received message %s from %s at %s" % (
                message.subject,
                message.from_header,
                message.processed,
            ))
            if options['confirm'] and not self.yes_or_no_question('Process this message?'):
                continue
            url = self.get_import_url(message)
            logger.debug("Import URL %s" % url)
            source = self.get_source(url)
            if options['confirm'] and self.yes_or_no_question(
                    'Reset known points?',
                    default_yes=False,
                ):
                source.data['known_points'] = {}
            if options['confirm'] and self.yes_or_no_question(
                    'Delete existing associated snapshots?',
                    default_yes=False,
                ):
                LocationSnapshot.objects\
                    .filter(source=source)\
                    .delete()
            if self.is_finish_email(message):
                logger.info("Is finishing e-mail.")
                source.active = False
            self.process_source(source)
            if options['confirm'] and not self.yes_or_no_question('Mark as read?'):
                logger.debug("Skipped.")
            else:
                message.read = datetime.datetime.utcnow().replace(tzinfo=utc)
                message.save()
                logger.debug("Marked as read.")
        
        for ongoing_source in LocationSource.objects.filter(active=True):
            self.process_source(ongoing_source)

    def yes_or_no_question(self, question, default_yes=True):
        if default_yes:
            default_string = '([y]/n)'
            default_answer = 'y'
        else:
            default_string = '(y/[n])'
            default_answer = 'n'
        result = False
        while result == False:
            result = raw_input('%s %s: ' % (
                question,
                default_string,
            )).lower()
            if result == '':
                result = default_answer
            if result not in ('y', 'n', ):
                print "Please enter either 'y' or 'n'.\n"
                result = False
        if result == 'y':
            return True
        return False

    def process_source(self, source):
        logger.info("Processing source %s" % source)
        document = self.get_document(source.data['url'])
        start_time = self.get_start_time(document)
        points = self.get_points(document)
        route_name = self.get_route_name(document)

        max_date = self.get_max_date(source)
        points_created = 0
        points_skipped = 0
        for data_point in points:
            key_name = data_point['key']
            point_date = start_time + datetime.timedelta(
                        seconds = data_point['time']
                        )
            if isinstance(source.data['known_points'], list):
                source.data['known_points'] = {}
            if key_name not in source.data['known_points'].keys():
                logger.debug("Point %s,%s at %s not in known points" % (
                        data_point['lat'],
                        data_point['lng'],
                        point_date
                    ))
                if max_date:
                    min_next_date = max_date + datetime.timedelta(seconds=MINIMUM_INTERVAL_SECONDS)
                else:
                    min_next_date = None
                if not max_date or (min_next_date and min_next_date < point_date):
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
                    points_created += 1
                    logger.debug("Creating point %s,%s at %s" % (
                            data_point['lat'],
                            data_point['lng'],
                            point_date
                        ))
                else:
                    if min_next_date:
                        logger.debug('%s - %s = %s seconds' % (
                            min_next_date,
                            point_date,
                            (min_next_date - point_date).seconds
                            ))
                    logger.debug("Minimum point interval not exceeded for %s,%s at %s" % (
                            data_point['lat'],
                            data_point['lng'],
                            point_date
                        ))
                    points_skipped += 1
                source.data['known_points'][key_name] = data_point
            else:
                logger.debug("Point %s,%s at %s already exists" % (
                    data_point['lat'],
                    data_point['lng'],
                    point_date
                ))
        logger.info('Created %s points between %s and %s (%s skipped)' % (
            points_created,
            self.get_min_date(source),
            self.get_max_date(source),
            points_skipped,
        ))
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

    def get_min_date(self, source):
        return LocationSnapshot.objects\
                .filter(source=source)\
                .aggregate(max_date=Min('date'))['max_date']

    def get_max_date(self, source):
        return LocationSnapshot.objects\
                .filter(source=source)\
                .aggregate(max_date=Max('date'))['max_date']

    def get_points(self, document):
        points = []
        coordinate_table = document.xpath('//abvio:coordinateTable', namespaces=self.namespaces)[0].text.split('\n')
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

    def get_document(self, url):
        return objectify.fromstring(
                urllib2.urlopen(url).read()
                )

    def get_import_url(self, message):
        matches = re.search(r"Import URL: (.*)", message.body)
        if not matches:
            return None
        return matches.groups()[0].strip()
