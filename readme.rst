.. image:: https://travis-ci.org/latestrevision/django-location.png?branch=master
   :target: https://travis-ci.org/latestrevision/django-location

django-location
===============

Do you check-in on `Foursquare <http://foursquare.com/>`__? Do you track
your runs or bike commutes with
`Runmeter <http://www.abvio.com/runmeter/>`__? Do you use an IOS device?
Why let third-party interfaces be your only window into your day-to-day
movements?

This Django application will consume location information provided by
Foursquare, iCloud, and, if you happen to be a user of it, Runmeter, and
store it in your database for display at will.

Installation
------------

You can either install from pip::

    pip install django-location


*or* checkout and install the source from the `github
repository <https://github.com/latestrevision/django-location>`__::

    git clone https://github.com/latestrevision/django-location.git
    cd django-location
    python setup.py install

You'll want to add both django-social-auth and django-location to your
project's ``urls.py``; you can technically use whatever URL you'd like,
but for the purposes of the instructions below, we'll expect that you'll
add them like::

    url(r'^location/', include('location.urls')),
    url(r'', include('social_auth.urls')),

Recommended Extra Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~

Each point gathered will also be able to provide to you what
neighborhood and city it is in if the following two packages are
installed:

-  `django-neighborhoods <http://github.com/latestrevision/django-neighborhoods/>`__
-  `django-census-places <http://github.com/latestrevision/django-census-places/>`__

Location Sources
----------------

For some of the below consumers, iCloud and Runmeter specifically, you will
need to set up a cron job that will handle certain periodic tasks, you can
do this by adding a cron job running::

    python /path/to/your/manage.py location_consumer

I'd suggest running this at five or ten minute intervals, but selecting longer
intervals will have only minor effects; either reducing sample frequency 
(in the case of the iCloud consumer) or increasing update latency (in the
case of the Runmeter consumer).

Foursquare
~~~~~~~~~~

`Foursquare <http://foursquare.com/>`__ has options in its consumer
settings to allow it to instantly post check-in information to an API
endpoint that this application provides. To support that, you'll need to
do the following:

1. Go to the `Foursquare developer
   site <http://developer.foursquare.com/>`__ and create a new consumer.

   -  Enter the callback URL for django-social-auth's Foursquare backend
      (generally http://yourdomain.com/complete/foursquare/).
   -  Turn on Push API notifications ('Push checkins by this consumer's
      users').
   -  Enter the push URL for the django-location app (usually
      https://yourdomain.com/location/foursquare/). Note: Foursquare
      requires that the connection be made via HTTPs.

2. Configure the following settings::

       FOURSQUARE_CONSUMER_KEY = "THECLIENTIDYOUJUSTGENERATED"
       FOURSQUARE_CONSUMER_SECRET  = "THECLIENTSECRETYOUJUSTGENERATED"

3. Go to the configuration URL for the django-location app (usually
   http://yourdomain.com/admin/location/locationsource/configure-accounts/)
   while logged-in to the admin, and click on the 'Authorize Foursquare'
   button. This will bring you to Foursquare's site using your
   configured options, and authorize your web application to receive
   check-ins from the user with which you log-into Foursquare.
4. If everything is set-up, you shouldn't need to do anything more, but
   Foursquare does offer a 'Send a test push' button on their consumer
   console that you can use to verify that everything is properly
   connected.

Runmeter
~~~~~~~~

`Runmeter <http://www.abvio.com/runmeter/>`__ does not provide an API,
but does allow you to configure the application to send out e-mail
notifications when you begin (and finish, etc) your run, bike, or
anything else. To consume information from Runmeter, we'll configure it
to e-mail to an otherwise-unused e-mail inbox (important), and configure
django-location to consume those e-mail messages and extract coordinates
from the linked-to KML file.

1. Configure the Runmeter application to send start and finish
   notifications to a mailbox accessible by POP3 or IMAP.
2. Set-up Django Mailbox to consume mail from such a mailbox (consult
   `django-mailbox's
   documentation <http://github.com/latestrevision/django-mailbox/>`__).
3. Update users' Location Consumer Settings record to set the field 
   ``runmeter_email`` to match the e-mail address from which a user's device
   will be sending Runmeter updates.

iCloud
~~~~~~

`iCloud <https://www.icloud.com/>`__ provides a service named 'Find my iPhone'
that allows you to request your device's location at-will.  This library
provides you with an easy way to use this service's location information
as one of your location sources.

1. Identify the devices associated with your account, you can
   do that by using the ``list_icloud_devices`` management command::

    python /path/to/your/manage.py list_icloud_devices <icloud username> <icloud password>

   replacing ``<icloud username>`` and ``<icloud password>`` with your
   iCloud username and password.
   
   This will print a list of devices and their IDs; in my case, it prints
   something like this::

    Name: MacBook Air 11": sinclair -- ID: reGYDh9XwqNWTGIhNBuEwP1ds0F/Lg5t/fxNbZ3V939hhXawByErk+HYVNSUzmWV
    Name: iPhone 4S: Adam Coddingtons iPhone -- ID: i9vbKRGIcLYqJnXMc1b257kUWnoyEBcEh6yM+IfmiMLh7BmOpALU+w==

2. Update users' Location Consumer Settings records to include the user's
   ``iCloud username``, ``iCloud password``, and ``iCloud device ID`` from
   which you would like to gather location information.

Displaying Location Using a Template Tag
----------------------------------------

You can use the ``current_location`` template tag to gather the most
recent location for a given user.

Simple example::

    {% load current_location %}
    {% current_location of 'adam' as location_of_adam %}

    <p>
        {{ location_of_adam.user.username }} is at {{ location_of_adam.location.coords.1 }}, {{ location_of_adam.location.coords.0 }}
    </p>

If you have installed 'django-neighborhoods' and 'django-census-places',
you can also print city and neighborhood information::

    {% load current_location %}
    {% current_location of 'adam' as location_of_adam %}

    <p>
        {{ location_of_adam.user.username }} is in the {{ location_of_adam.neighborhood.name }} neighborhood of {{ location_of_adam.city.name }}, {{ location_of_adam.city.get_state_display }}.
    </p>

You might not always have neighborhood or city information for a given
point, and maybe you would like to display a map using the Google Maps
API; here's a fleshed-out version::

    {% load current_location %}
    <script src="http://maps.google.com/maps/api/js?sensor=true" type="text/javascript"></script>

    {% current_location of 'somebody' as location %}
    {{ location.user.username }} is
    {% if location.neighborhood %}
        in the {{ location.neighborhood.name }} neighborhood of {{ location.neighborhood.city }},
        {{ location.neighborhood.state }}:
    {% elif location.city %}
        in {{ location.city.name }}, {{ location.city.get_state_display }}:
    {% else %}
        ({{ location.get_nearest_city.distance.mi }} miles from {{ location.get_nearest_city.name }}):
    {% endif %}
    <div id="my_location_map" style="width: 100%; height: 400px;"></div>
    <script type="text/javascript">
        var myLocation = document.getElementById('my_location_map');
        myLocation.gmap({
            'center': '{{ location.location.coords.1 }},{{ location.location.coords.0 }}',
            'zoom': 10,
            'mapTypeId': google.maps.MapTypeId.HYBRID
        });
        myLocation.gmap('addMarker', {
            'position': '{{ location.location.coords.1 }},{{ location.location.coords.0 }}',
        });
    </script>


.. image:: https://d2weczhvl823v0.cloudfront.net/latestrevision/django-location/trend.png
   :alt: Bitdeli badge
   :target: https://bitdeli.com/free

