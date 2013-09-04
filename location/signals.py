from django.dispatch.dispatcher import Signal

from location.models import LocationSnapshot


location_updated = Signal(providing_args=['user', 'from_', 'to'])
location_changed = Signal(providing_args=['user', 'from_', 'to'])


class watch_location(object):
    def __init__(self, user):
        self.user = user

    def _get_current_location(self):
        return LocationSnapshot.objects.filter(
            source__user=self.user,
        ).order_by('-date')[0]

    def __enter__(self):
        self.original_location = None
        try:
            self.original_location = self._get_current_location()
        except IndexError:
            pass
        return self

    def __exit__(self, *args):
        current_location = self._get_current_location()
        if self.original_location != current_location:
            location_updated.send(
                sender=self,
                user=self.user,
                from_=self.original_location,
                to=current_location,
            )
            if (
                self.original_location and
                self.original_location.location
                != current_location.location
            ):
                location_changed.send(
                    sender=self,
                    user=self.user,
                    from_=self.original_location,
                    to=current_location,
                )
