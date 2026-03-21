from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse, resolve

from main.pm25_colors import pm25_to_rgb


class CustomUserTests(TestCase):
    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="will", email="will@email.com", password="testpass123"
        )
        self.assertEqual(user.username, "will")
        self.assertEqual(user.email, "will@email.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username="superadmin", email="superadmin@email.com", password="testpass123"
        )
        self.assertEqual(admin_user.username, "superadmin")
        self.assertEqual(admin_user.email, "superadmin@email.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)


class Pm25ToRgbTests(TestCase):
    def test_missing_is_grey(self):
        self.assertEqual(pm25_to_rgb(None), (128, 128, 128))

    def test_band_boundaries_match_map_scale(self):
        self.assertEqual(pm25_to_rgb(0), (80, 240, 230))
        self.assertEqual(pm25_to_rgb(9.9), (80, 240, 230))
        self.assertEqual(pm25_to_rgb(10), (80, 204, 170))
        self.assertEqual(pm25_to_rgb(24.9), (240, 230, 65))
        self.assertEqual(pm25_to_rgb(25), (255, 80, 80))
        self.assertEqual(pm25_to_rgb(49.9), (255, 80, 80))
        self.assertEqual(pm25_to_rgb(50), (150, 0, 50))
        self.assertEqual(pm25_to_rgb(74.9), (150, 0, 50))
        self.assertEqual(pm25_to_rgb(75), (125, 33, 129))
        self.assertEqual(pm25_to_rgb(200), (125, 33, 129))


class SignupPageTests(TestCase):
    username = "newuser"
    email = "newuser@email.com"
    
    def setUp(self):
        url = reverse("account_signup")
        self.response = self.client.get(url)
    
    def test_signup_template(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, "account/signup.html")
        self.assertContains(self.response, "Sign Up")
        self.assertNotContains(self.response, "Hi there! I should not be on the page.")
    
    def test_signup_form(self):
        new_user = get_user_model().objects.create_user(self.username, self.email)
        self.assertEqual(get_user_model().objects.all().count(), 1)
        self.assertEqual(get_user_model().objects.all()[0].username, self.username)
        self.assertEqual(get_user_model().objects.all()[0].email, self.email)