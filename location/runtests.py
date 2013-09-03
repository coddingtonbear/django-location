#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.contrib.gis.db.backends.spatialite',
                'NAME': ':memory:'
            },
        },
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
