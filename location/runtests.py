#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings


LOCAL_TESTING = False
if '--local' in sys.argv:
    LOCAL_TESTING = True
    sys.argv.remove('--local')


if not settings.configured:
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'postgis_adapter_test',
            'USERNAME': 'postgres',
            'HOST': '127.0.0.1'
        }
    }
    if LOCAL_TESTING:
        DATABASES = {
            'default': {
                'ENGINE': 'django.contrib.gis.db.backends.spatialite',
                'NAME': ':memory:'
            },
        }
    settings.configure(
        DATABASES=DATABASES,
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'location',
        ],
        USE_TZ=True,
    )

from django.test.simple import DjangoTestSuiteRunner


def runtests(*test_args):
    if not test_args:
        test_args = ['location']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)

    if LOCAL_TESTING:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT InitSpatialMetaData();")

    runner = DjangoTestSuiteRunner(
        verbosity=1,
        interactive=False,
        failfast=False
    )
    failures = runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
