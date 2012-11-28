from setuptools import setup

setup(
    name='django-location',
    version='1.1.6',
    url='http://bitbucket.org/latestrevision/django-location/',
    description='Gather, store, and display real-time location information from Foursquare, Google Latitude, and more.',
    author='Adam Coddington',
    author_email='me@adamcoddington.net',
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: GIS',
    ],
    include_package_data=True,
    extras_require={
            'locationdetails': [
                'django-neighborhoods',
                'django-census-places',
            ],
            'runmeter': [
                'django-mailbox',
            ],
            'kml': [
                'pykml',
            ]
        },
    install_requires=[
        'django>=1.4',
        'django-social-auth',
        'pytz',
        'requests',
        'jsonfield',
        'lxml',
        ],
    packages=[
        'location',
        'location.management',
        'location.management.commands',
        'location.migrations',
        'location.templatetags',
        ],
)
