from setuptools import setup

setup(
    name='django-location',
    version='1.5.1',
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
            ],
            'icloud': [
                'pyicloud',
            ]
        },
    install_requires=[
        'django>=1.4',
        'django-social-auth',
        'pytz',
        'requests>=1.2.0',
        'jsonfield>=0.9.15',
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
