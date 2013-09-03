from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from location.consumers.foursquare import FoursquareConsumer


@csrf_exempt
def foursquare_checkin(request):
    consumer = FoursquareConsumer(
        request.POST.get('checkin', None)
    )
    consumer.process_checkin()
    return HttpResponse("OK")
