from distutils.core import setup

setup(
    name='django-location',
    version='0.1',
    url='http://bitbucket.org/latestrevision/django-location/',
    description='Gather, store, and display real-time location information from Foursquare, Google Latitude, and more.',
    author='Adam Coddington',
    author_email='me@adamcoddington.net',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    packages=[
        'location',
        'location.management',
        'location.management.commands',
        'location.migrations',
        'location.templatetags',
        ],
)
