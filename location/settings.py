import copy

from django.conf import settings


DEFAULT_SETTINGS = {
    'cache_prefix': 'LOCATION',
    'runmeter_mailbox': None,
    'icloud': {
        'min_horizontal_accuracy': 20,
        'max_wait_seconds': 120,
        'request_interval_seconds': 5,
    },
    'periodic_consumers': [
        'location.consumers.runmeter.RunmeterConsumer',
        'location.consumers.icloud.iCloudConsumer',
    ]
}

SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)
SETTINGS.update(
    getattr(
        settings,
        'DJANGO_LOCATION_SETTINGS',
        {}
    )
)
