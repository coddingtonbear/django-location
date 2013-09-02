import datetime
import logging

from django.conf import settings
from django.contrib.gis.db import models
from django.core.cache import cache
from django.dispatch import receiver
from jsonfield.fields import JSONField

from location.settings import SETTINGS


logger = logging.getLogger('location.models')


try:
    from census_places.models import PlaceBoundary
except ImportError:
    logger.warning(
        "django-census-places is not installed, locations will not "
        "be populated with city information."
    )
    PlaceBoundary = None
try:
    from neighborhoods.models import Neighborhood
except ImportError:
    logger.warning(
        "django-neighborhoods is not installed, locations will not "
        "be populated with neighborhood information."
    )
    Neighborhood = None
try:
    from django_mailbox.signals import message_received
except ImportError:
    logger.warning(
        "django-mailbox is not installed, cannot consume messages "
        "from runmeter."
    )
    message_received = None


class LocationConsumerSettings(models.Model):
    user = models.OneToOneField(
        getattr(
            settings,
            'AUTH_USER_MODEL',
            'auth.User'
        ),
        related_name='location_consumer_settings'
    )
    icloud_enabled = models.BooleanField(default=False)
    icloud_timezone = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default='US/Pacific',
    )
    icloud_username = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    icloud_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    icloud_device_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=(
            "Device ID of the iCloud device from which to gather periodic"
            "location updates"
        )
    )
    runmeter_enabled = models.BooleanField(default=False)
    runmeter_email = models.EmailField(
        max_length=255,
        help_text=(
            "E-mail address of the device from which RunMeter will be sending"
            "location updates"
        )
    )

    def __unicode__(self):
        return "Location Consumer Settings for %s" % (
            self.user.get_username()
        )

    class Meta:
        verbose_name = 'Location Consumer Settings'
        verbose_name_plural = 'Location Consumer Settings'


class LocationSourceType(models.Model):
    name = models.CharField(max_length=255)
    icon = models.ImageField(
        null=True,
        blank=True,
        upload_to='source_type_icons/'
    )

    def __unicode__(self):
        return self.name


class LocationSource(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(
        getattr(
            settings,
            'AUTH_USER_MODEL',
            'auth.User'
        ),
        related_name='location_sources',
        null=True,
        default=None,
    )
    type = models.ForeignKey(LocationSourceType)
    data = JSONField()
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(
        auto_now=True
    )
    active = models.BooleanField(
        default=False
    )

    def __unicode__(self):
        return "%s: %s" % (
            self.type.name,
            self.name,
        )


class LocationSnapshot(models.Model):
    location = models.PointField(
        geography=True,
        spatial_index=True
    )
    source = models.ForeignKey(
        LocationSource,
        related_name='points',
        null=True,
        blank=True
    )
    date = models.DateTimeField(
        default=datetime.datetime.now
    )

    created = models.DateTimeField(
        auto_now_add=True
    )

    objects = models.GeoManager()

    def get_cache_key(self, name):
        return '%s:%s:%s:%s' % (
            SETTINGS['cache_prefix'],
            self.__class__.__name__,
            self.pk,
            name
        )

    def get_cached(self, name):
        return cache.get(self.get_cache_key(name))

    def set_cached(self, name, value):
        cache.set(self.get_cache_key(name), value, 60 * 60 * 24)

    @property
    def city(self):
        if PlaceBoundary:
            cached = self.get_cached('city')
            if cached:
                return cached
            try:
                result = PlaceBoundary.get_containing(self.location)
                self.set_cached('city', result)
                return result
            except PlaceBoundary.DoesNotExist:
                pass
        return None

    @property
    def neighborhood(self):
        if Neighborhood:
            cached = self.get_cached('neighborhood')
            if cached:
                return cached
            try:
                result = Neighborhood.get_containing(self.location)
                self.set_cached('neighborhood', result)
                return result
            except Neighborhood.DoesNotExist:
                pass
        return None

    def find_nearest_city(self):
        if PlaceBoundary:
            cached = self.get_cached('nearest_city')
            if cached:
                return cached
            try:
                result = PlaceBoundary.get_nearest_to(self.location)
                self.set_cached('nearest_city', result)
                return result
            except PlaceBoundary.DoesNotExist:
                pass
        return None

    def __unicode__(self):
        return u"%s's location at %s" % (
            self.source.user,
            self.date
        )


if message_received:
    @receiver(message_received, dispatch_uid='process_incoming_runmeter_msg')
    def process_incoming_runmeter_message(sender, message, **kwargs):
        from location.consumers.runmeter import RunmeterConsumer
        if message.mailbox.name == SETTINGS['runmeter_mailbox']:
            RunmeterConsumer.process_message(message)
