import logging

from django import template
from django.conf import settings
from django.contrib.gis.geos import Point

from location.models import LocationSnapshot

register = template.Library()

logger = logging.getLogger('location.templatetags.current_location')

LOCATION_HOME = getattr(settings, 'LOCATION_HOME', None)


class LocationSnapshotNode(template.Node):
    def __init__(self, variable, username):
        self.username = username
        self.variable = variable

    def render(self, context):
        try:
            snapshot_query = LocationSnapshot.objects.filter(
                source__user__username=self.username
            ).order_by('-date')
            if LOCATION_HOME:
                snapshot_query = snapshot_query.distance(
                    Point(
                        *LOCATION_HOME
                    )
                )
            snapshot = snapshot_query[0]
            logger.info(snapshot)
        except IndexError:
            logger.info('No snapshot available')
            snapshot = None
        context[self.variable] = snapshot
        return ''


@register.tag(name='current_location')
def do_get_current_location(parser, token):
    tag, of_kwd, username, as_kwd, variable = token.split_contents()
    return LocationSnapshotNode(variable, username[1:-1])
