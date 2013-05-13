import datetime
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.core.cache import cache
from jsonfield.fields import JSONField

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


CACHE_PREFIX = getattr(
    settings,
    'DJANGO_LOCATION_CACHE_PREFIX',
    'LOCATION',
)


class LocationSourceType(models.Model):
    name = models.CharField(max_length=255)
    icon = models.ImageField(
            null=True,
            blank=True,
            upload_to='source_type_icons/'
            )
    ttl_seconds = models.PositiveIntegerField(
            default=3600,
            help_text=(
                "TTL (Time to live) for coordinates of this type.  Generally, "
                "this should store the median amount of time between "
                "individual LocationSnapshot instances of this type.  It is "
                "additionally used for implied accuracy -- a point with a high "
                "TTL is expected to be less-accurate than a point with a low "
                "TTL."
            )
        )
    
    def __unicode__(self):
        return self.name

class LocationSource(models.Model):
    name = models.CharField(max_length=255)
    type = models.ForeignKey(LocationSourceType)
    data = JSONField()
    created = models.DateTimeField(
                auto_now_add=True
            )
    updated = models.DateTimeField(
                auto_now=True
            )
    active = models.BooleanField(
                default = False
            )

    def __unicode__(self):
        return "%s: %s" % (
                self.type.name,
                self.name,
            )

class LocationSnapshot(models.Model):
    user = models.ForeignKey(User)
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
                default = datetime.datetime.now
            )

    created = models.DateTimeField(
                auto_now_add = True
            )

    objects = models.GeoManager()

    def get_cache_key(self, name):
        return '%s:%s:%s:%s' % (
            CACHE_PREFIX,
            self.__class__.__name__,
            self.pk,
            name
        )

    def get_cached(self, name):
        return cache.get(
            self.get_cache_key(name)
        )

    def set_cached(self, name, value):
        cache.set(
            self.get_cache_key(name),
            value
        )

    @property
    def city(self):
        cached = self.get_cached('city')
        if cached:
            return cached
        if PlaceBoundary:
            try:
                return PlaceBoundary.get_containing(self.location)
            except PlaceBoundary.DoesNotExist:
                pass
        return None

    @property
    def neighborhood(self):
        cached = self.get_cached('neighborhood')
        if cached:
            return cached
        if Neighborhood:
            try:
                return Neighborhood.get_containing(self.location)
            except Neighborhood.DoesNotExist:
                pass
        return None

    def find_nearest_city(self):
        cached = self.get_cached('nearest_city')
        if cached:
            return cached
        if PlaceBoundary:
            try:
                return PlaceBoundary.get_nearest_to(self.location)
            except PlaceBoundary.DoesNotExist:
                pass
        return None

    def __unicode__(self):
        return u"%s's location at %s" % (
                    self.user,
                    self.date
                )
