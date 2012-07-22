from django.contrib.gis import admin
from location.models import LocationSnapshot, LocationSource, LocationSourceType

class LocationSourceAdmin(admin.options.OSMGeoAdmin):
    list_display = (
                'created',
                'name',
                'type',
                'active'
            )
    ordering = ['-created']

class LocationSnapshotAdmin(admin.options.OSMGeoAdmin):
    list_display = (
                'date',
                'neighborhood',
                'nearest_city',
                'user',
            )
    date_hierarchy = 'date'
    raw_id_fields = ('source', )
    list_per_page = 25
    ordering = ['-date']

    def nearest_city(self, obj):
        nearest = obj.find_nearest_city()
        if nearest.distance != None:
            return "%s (%d mi away)" % (
                        nearest,
                        nearest.distance.mi
                    )
        return nearest


admin.site.register(LocationSourceType)
admin.site.register(LocationSource, LocationSourceAdmin)
admin.site.register(LocationSnapshot, LocationSnapshotAdmin)
