from django.test import TestCase
from django.contrib.auth.models import User
from photo.models import *
from django.test import Client
from django.conf import settings
import os
import sys

FIXTURE = 'photo_test_fixture.json'
TEST_ROOT = os.path.abspath(os.path.dirname(__file__))

class ImagemodelTestCase(TestCase):
    """ Test if Image model is created """
    fixtures = [FIXTURE, ]
    def setUp(self):
        self.user = User.objects.get(pk=1)
    def test_unicode(self):
        expected = "compy.jpg"
        p1 = Image(image="compy.jpg", title=expected)
        actual = unicode(p1)
        self.assertEqual(expected, actual)

class AlbummodelTestCase(TestCase):
    """ Test if Album model is created """
    def test_unicode(self):
        expected = "Test_Album"
        alb = Album(title=expected)
        actual = unicode(alb)
        self.assertEqual(expected, actual)

class TagmodelTestCase(TestCase):
    """ Test if Tag model is created """
    def test_unicode(self):
        expected = "nature"
        tg = Tag(tag = expected)
        actual = unicode(tg)
        self.assertEqual(expected, actual)

class HomepageUrlTestCase(TestCase):    
    """View Image, search would need Image to be uploaded.
    For this excerise we did not write forms for upload by our own 
    So excluding the Image upload, view tests from this.
    Test if mainpage url is responsive """
    
    def setUp(self):
        #set up dummy client, a dummy album
        self.client = Client()
        self.alb = Album.objects.create(title="Tests", public="True")
    
    def test_url_homepage(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
    
    def test_url_public_album(self):
        response = self.client.get('/1/')
        self.assertEqual(response.status_code, 200)
        
class LoginTestCase(TestCase):
    """ Test login """
    def test_login(self):
        c = Client()
        response = c.post('/login/', {'username': 'admin', 'password': 'admin'})
        self.assertEqual(response.status_code, 200)

class ThumbnailSaveTestCase(TestCase):
    """ Actual image is uploaded through the admin, we did not 
    write form by our own. So providing a path to a photo for 
    'image' field of model Image is not actually an 'upload'.
    So we are excluding the test for upload image.  
    But save method on that would need to create thumbnails"""
    def setUp(self):
        # override MEDIA_ROOT for this test
        self._old_MEDIA_ROOT = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = os.path.join(TEST_ROOT, 'testdata/media/')
        self.photo = Image(image='mi3.jpeg', title='test-pic')

    def tearDown(self):
        # reset MEDIA_ROOT
        settings.MEDIA_ROOT = self._old_MEDIA_ROOT
        #delete thumbnails created (This rm command is dangerous)
        del_files = "rm -rf " + TEST_ROOT + "/testdata/media/images/*"
        os.system(del_files)        

    def test_thum_image(self):
        self.photo.save()        
        #Usually thumbnials are prefixed with image name. Verify if thumbnail got created 
        #and then teardown will delete the thumbnails created images folder in testdata.
        self.assertTrue(self.photo.image.name.split('.')[0] in self.photo.thumbnail.name)

