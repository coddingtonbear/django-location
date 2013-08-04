from setuptools import setup

requirements = []
with open('requirements.txt', 'r') as in_:
    requirements = in_.readlines()

setup(
    name='django-location',
    version='1.6',
    url='http://bitbucket.org/latestrevision/django-location/',
    description='Gather, store, and display real-time location information from Foursquare, iCloud, and more.',
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
    install_requires=requirements,
    packages=[
        'location',
        'location.management',
        'location.management.commands',
        'location.migrations',
        'location.templatetags',
    ],
)
