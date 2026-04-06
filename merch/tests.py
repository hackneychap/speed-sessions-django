from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from communities.models import Community
from merch.models import MerchItem
from django.core.files.uploadedfile import SimpleUploadedFile
import io
from PIL import Image

def create_test_image(size_kb=100):
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'test.png'
    file.seek(0)
    # If we need to force a specific file size
    if size_kb > 0:
        content = file.read()
        padding = b'0' * (size_kb * 1024 - len(content))
        return SimpleUploadedFile('test.png', content + padding, content_type='image/png')
    return SimpleUploadedFile('test.png', file.read(), content_type='image/png')

class MerchManagementTest(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='manager', password='password123')
        self.other_user = User.objects.create_user(username='other', password='password123')
        self.community = Community.objects.create(name='Test Comm', manager=self.manager)
        
        # Ensure profile exists (signal should handle it, but being explicit)
        self.manager.profile.community = self.community
        self.manager.profile.save()
        
        self.client = Client()

    def test_manager_can_add_merch_with_images(self):
        self.client.login(username='manager', password='password123')
        image = create_test_image()
        url = reverse('add-merch', kwargs={'slug': self.community.slug})
        
        data = {
            'name': 'Test Shirt',
            'description': 'Cool shirt',
            'price': '25.00',
            'available_sizes': 'S,M,L',
            'available_colors': 'Red,Blue',
            'images': [image]
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect to community page
        self.assertEqual(MerchItem.objects.filter(name='Test Shirt').count(), 1)
        item = MerchItem.objects.get(name='Test Shirt')
        self.assertEqual(item.images.count(), 1)

    def test_non_manager_cannot_add_merch(self):
        self.client.login(username='other', password='password123')
        url = reverse('add-merch', kwargs={'slug': self.community.slug})
        response = self.client.post(url, {'name': 'Hack'})
        self.assertEqual(response.status_code, 302) # Redirect away or 403
        self.assertEqual(MerchItem.objects.count(), 0)

    def test_image_limit_5(self):
        self.client.login(username='manager', password='password123')
        url = reverse('add-merch', kwargs={'slug': self.community.slug})
        
        images = [create_test_image() for _ in range(6)]
        data = {
            'name': 'Too Many Images',
            'description': 'Test',
            'price': '10.00',
            'available_sizes': 'S',
            'available_colors': 'Black',
            'images': images
        }
        
        response = self.client.post(url, data)
        # Should show error in form
        self.assertContains(response, "You can only upload up to 5 images.")
        self.assertEqual(MerchItem.objects.count(), 0)

    def test_image_size_limit_1mb(self):
        self.client.login(username='manager', password='password123')
        url = reverse('add-merch', kwargs={'slug': self.community.slug})
        
        large_image = create_test_image(size_kb=1100) # > 1MB
        data = {
            'name': 'Large Image',
            'description': 'Test',
            'price': '10.00',
            'available_sizes': 'S',
            'available_colors': 'Black',
            'images': [large_image]
        }
        
        response = self.client.post(url, data)
        self.assertContains(response, "Image file too large (limit 1MB)")
        self.assertEqual(MerchItem.objects.count(), 0)
