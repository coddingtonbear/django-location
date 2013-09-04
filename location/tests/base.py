from django.contrib.auth.models import User
from django.test import TestCase


class BaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='arbitrary_username',
        )
