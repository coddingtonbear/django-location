from setuptools import setup, find_packages

requirements = []
with open('requirements.txt', 'r') as in_:
    requirements = in_.readlines()

setup(
    name='django-location',
    version='2.0.4',
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
    },
    tests_require=[
        'mock>=1.0.1',
    ],
    test_suite='location.runtests.runtests',
    install_requires=requirements,
    packages=find_packages()
)
