from django.core.management.base import BaseCommand
import pyicloud


class Command(BaseCommand):
    args = '<apple icloud username> <apple icloud password>'
    help = 'List devices associated with this iCloud account'

    def handle(self, *args, **kwargs):
        icloud_username = args[0]
        icloud_password = args[1]

        api = pyicloud.PyiCloudService(icloud_username, icloud_password)

        for id, device in api.devices.items():
            print 'Name: %s -- ID: %s' % (
                str(device),
                str(id),
            )
