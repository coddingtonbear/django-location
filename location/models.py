import datetime
import logging

from django.contrib.auth.models import User
from django.contrib.gis.db import models
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

    @property
    def city(self):
        if PlaceBoundary:
            if not hasattr(self, '_city'):
                try:
                    self._city = PlaceBoundary.get_containing(self.location)
                except PlaceBoundary.DoesNotExist:
                    self._city = None
            return self._city

    @property
    def neighborhood(self):
        if Neighborhood:
            if not hasattr(self, '_neighborhood'):
                try:
                    self._neighborhood = Neighborhood.get_containing(self.location)
                except Neighborhood.DoesNotExist:
                    self._neighborhood = None
            return self._neighborhood

    def find_nearest_city(self):
        if PlaceBoundary:
            if not hasattr(self, '_nearest_city'):
                try:
                    self._nearest_city = PlaceBoundary.get_nearest_to(self.location)
                except PlaceBoundary.DoesNotExist:
                    self._nearest_city = None
            return self._nearest_city

    def __unicode__(self):
        return u"%s's location at %s" % (
                    self.user,
                    self.date
                )
