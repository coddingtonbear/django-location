Introduction
============

Do you share your location with Google Latitude?  Do you check-in on Foursquare?  Do you track your runs or bike commutes with Runmeter?  Why let third-party interfaces be your window into your day-to-day movements?

This Django application will consume location information provided by Foursquare, Google Latitude, and, if you happen to be a user of it, Runmeter, and store it in your database for display at will.

Requirements
------------

* django (using a GIS-capable database backend)
* django-social-auth (for OAuth keys used for communicating with Google Latitude)

### Recommended

Each point gathered will also be able to provide to you what neighborhood and city it is in if the following two packages are installed:

* django-neighborhoods
* django-census-places

If you'd like to consume Runmeter information, you'll need:

* django-mailbox (for reading incoming e-mail messages sent from the Runmeter app)

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

Consuming Foursquare Information
--------------------------------

Foursquare has options in its consumer settings to allow it to instantly post check-in information to an API endpoint that this application provides.
To support that, you'll need to do the following:

1. Go to the [Foursquare developer site](http://developer.foursquare.com/) and create a new consumer.
    a. Enter the callback URL for django-social-auth's Foursquare backend (generally 'http://yourdomain.com/complete/foursquare').
    b. Turn on Push API notifications ('Push checkins by this consumer's users').
    c. Enter the push URL for the django-location app (usually 'https://yourdomain.com/location/foursquare').  Note: Foursquare requires that the connection be made via HTTPs.
2. Configure the following settings:

        FOURSQUARE_CONSUMER_KEY = "THECLIENTIDYOUJUSTGENERATED"
        FOURSQUARE_CONSUMER_SECRET  = "THECLIENTSECRETYOUJUSTGENERATED"

3. Go to the configuration URL for the django-location app (usually 'https://yourdomain.com/location/configuration/') while logged-in to the admin, and click on the 'Configure Foursquare' link.  This will bring you to Foursquare's site using your configured options, and authorize your web application to receive check-ins from the user with which you log-into Foursquare.
3. If everything is set-up, you shouldn't need to do anything more, but Twitter does offer a 'Send a test push' button on their consumer console that you can use to verify that everything is properly connected.

Consuming Google Latitude Information
-------------------------------------

Google Latitude provides a RESTful interface for gathering a user's most recently known coordinates that can be wired-up to cron.

1. Go to the [Google API Console](https://code.google.com/apis/console/) and create a new project.
    * Be sure to turn on the Google Latitude API.
    * Go to the 'API Access' page and create an OAuth 2.0 Client ID.
        * Enter any 'Product Name' you'd like, and feel free to leave the 'Product Logo' field blank.
        * Select 'Web Application' as your application type.
        * Enter your domain as the site hostname.
        * Click 'Create Client ID'
    * Click 'Edit Settings' on your newly-created Client ID.
    * Enter the callback URL for django-social-auth's Google OAuth2 backend (generally 'http://yourdomain.com/complete/google-oauth2').
2. Configure the following settings:

        GOOGLE_OAUTH2_CLIENT_ID = "the.client.id.that.you.just.generated"
        GOOGLE_OAUTH2_CLIENT_SECRET = "the.client.secret.you.just.generated."
        GOOGLE_OAUTH_EXTRA_SCOPE = ["https://www.googleapis.com/auth/latitude.all.best"]
        GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {'access_type': 'offline'}

3. Go to the configuration URL for the django-location app (usually 'https://yourdomain.com/location/configuration/') while logged-in to the admin, and cick on the 'Configure Google OAuth2' link.  This will bring you to Foursquare's site using your configured options, and authorize your web application to gather location information from the Google Latitude API.
4. Wire up a cron job.
   * Instruct the cron job to run `python /path/to/your/manage.py update_latitude_location <django username>`
   * You are required to post no more than 1,000,000 requests per day, so, if you are gathering the latitude information for fewer than 695 accounts, you can safely run the job once per minute per user.

Consuming Runmeter Information
------------------------------

Additional requirements:

* `django-mailbox`

Configuration steps:

1. Configure the Runmeter application to send start and finish notifications to a mailbox accessible by POP3 or IMAP.
2. Set-up Django Mailbox to consume mail from such a mailbox (consult [django-mailbox's documentation](http://bitbucket.org/latestrevision/django-mailbox/)).
3. Wire up a cron job.
   a. Instruct the cron job to run `python /path/to/your/manage.py check_incoming_runmeter <name of mailbox>`
