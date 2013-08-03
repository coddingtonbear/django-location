Introduction
============

Do you check-in on [Foursquare](http://foursquare.com/)?  Do you track your runs or bike commutes with [Runmeter](http://www.abvio.com/runmeter/)?  Do you use an IOS device?  Why let third-party interfaces be your window into your day-to-day movements?

This Django application will consume location information provided by Foursquare, iCloud, and, if you happen to be a user of it, Runmeter, and store it in your database for display at will.

**Note**: Although this library will allow you to consume location information from Google Latitude, Google has announced that they will be discontinuing their Latitude service as of August 9th. If you are using an IOS device, consider switching to the (higher quality) iCloud location consumer.

Recommended Extra Packages
--------------------------

Each point gathered will also be able to provide to you what neighborhood and city it is in if the following two packages are installed:

* [django-neighborhoods](http://bitbucket.org/latestrevision/django-neighborhoods/)
* [django-census-places](http://bitbucket.org/latestrevision/django-census-places/)

If you'd like to consume Runmeter information, you'll need:

* [django-mailbox](http://bitbucket.org/latestrevision/django-mailbox/) (for reading incoming e-mail messages sent from the Runmeter app)

Installation
------------

You can either install from pip:

    pip install django-location

*or* checkout and install the source from the [bitbucket repository](https://bitbucket.org/latestrevision/django-location):

    hg clone https://bitbucket.org/latestrevision/django-location
    cd django-location
    python setup.py install

*or* checkout and install the source from the [github repository](https://github.com/latestrevision/django-location):

    git clone https://github.com/latestrevision/django-location.git
    cd django-location
    python setup.py install

You'll want to add both django-social-auth and django-location to your project's `urls.py`; you can technically use whatever URL you'd like, but for the purposes of the instructions below, we'll expect that you'll add them like:

    url(r'^location/', include('location.urls')),
    url(r'', include('social_auth.urls')),

Template Tags
-------------

You can use the `current_location` template tag to gather the most recent location for a given user.  

Simple example:

    {% load current_location %}
    {% current_location of 'adam' as location_of_adam %}

    <p>
        {{ location_of_adam.user.username }} is at {{ location_of_adam.location.coords.1 }}, {{ location_of_adam.location.coords.0 }}
    </p>

If you have installed 'django-neighborhoods' and 'django-census-places', you can also print city and neighborhood information:

    {% load current_location %}
    {% current_location of 'adam' as location_of_adam %}

    <p>
        {{ location_of_adam.user.username }} is in the {{ location_of_adam.neighborhood.name }} neighborhood of {{ location_of_adam.city.name }}, {{ location_of_adam.city.get_state_display }}.
    </p>

You might not always have neighborhood or city information for a given point, and maybe you would like to display a map using the Google Maps API; here's a fleshed-out version:

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

Consuming Foursquare Check-ins
------------------------------

[Foursquare](http://foursquare.com/) has options in its consumer settings to allow it to instantly post check-in information to an API endpoint that this application provides.
To support that, you'll need to do the following:

1. Go to the [Foursquare developer site](http://developer.foursquare.com/) and create a new consumer.
    * Enter the callback URL for django-social-auth's Foursquare backend (generally http://yourdomain.com/complete/foursquare/).
    * Turn on Push API notifications ('Push checkins by this consumer's users').
    * Enter the push URL for the django-location app (usually https://yourdomain.com/location/foursquare/).  Note: Foursquare requires that the connection be made via HTTPs.
2. Configure the following settings:

        FOURSQUARE_CONSUMER_KEY = "THECLIENTIDYOUJUSTGENERATED"
        FOURSQUARE_CONSUMER_SECRET  = "THECLIENTSECRETYOUJUSTGENERATED"

3. Go to the configuration URL for the django-location app (usually http://yourdomain.com/admin/location/locationsource/configure-accounts/) while logged-in to the admin, and click on the 'Authorize Foursquare' button.  This will bring you to Foursquare's site using your configured options, and authorize your web application to receive check-ins from the user with which you log-into Foursquare.
3. If everything is set-up, you shouldn't need to do anything more, but Foursquare does offer a 'Send a test push' button on their consumer console that you can use to verify that everything is properly connected.

Consuming Runmeter Paths
------------------------

[Runmeter](http://www.abvio.com/runmeter/) does not provide an API, but does allow you to configure the application to send out e-mail notifications when you begin (and finish, etc) your run, bike, or anything else.  To consume information from Runmeter, we'll configure it to e-mail to an otherwise-unused e-mail inbox (important), and configure django-location to consume those e-mail messages and extract coordinates from the linked-to KML file.

1. Configure the Runmeter application to send start and finish notifications to a mailbox accessible by POP3 or IMAP.
2. Set-up Django Mailbox to consume mail from such a mailbox (consult [django-mailbox's documentation](http://bitbucket.org/latestrevision/django-mailbox/)).
3. Wire up a cron job.
    * Instruct the cron job to run `python /path/to/your/manage.py check_incoming_runmeter <name of mailbox>`

