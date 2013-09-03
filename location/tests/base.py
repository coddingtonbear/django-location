from django.contrib.auth.models import User
from django.test import TestCase
import mimic
import stubout


class BaseTestCase(TestCase):
    __metaclass__ = mimic.MimicMetaTestBase

    def setUp(self):
        self.mimic = mimic.Mimic()
        self.stubs = stubout.StubOutForTesting()
        self.user = User.objects.create(
            username='arbitrary_username',
        )
