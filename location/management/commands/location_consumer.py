import logging
from optparse import make_option

from django.core.management.base import BaseCommand
from django.db import transaction

from location.settings import SETTINGS


logger = logging.getLogger(__name__)


def get_class_by_path(path):
    mod = __import__('.'.join(path.split('.')[:-1]))
    components = path.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--loglevel',
            default=None,
        ),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        # Only set logging if it isn't already configured
        if options['loglevel'] is not None:
            logging.basicConfig(
                level=logging.getLevelName(options['loglevel'])
            )

        for consumer_path in SETTINGS['periodic_consumers']:
            logger.info("Running periodic consumer '%s'.", consumer_path)
            try:
                consumer_cls = get_class_by_path(consumer_path)
                consumer_cls.periodic()
            except ImportError:
                logger.exception('Unable to import consumer.')
            except:
                logger.exception('Error encountered while executing consumer.')
