from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from string import join
import os
from PIL import Image as PImage
from django.conf import settings
from django.core.files import File
from os.path import join as pjoin
from tempfile import *

class Tag(models.Model):
    """ Tag is the many to many field with Image
    An image can be associated with multiple tags """
    tag = models.CharField(max_length=50)
    user = models.ForeignKey(User, null=True, blank=True)
    def __unicode__(self):
        return self.tag

class Image(models.Model):
    """ Image model is for uploading photos, creating thumbnail, 
    and retaining the orientation. Resizing the image for display
    is a significant performance issue. We are not using the cache,
    so for the sake of simplicity we will store copy of thumbnailsize
    when an image is added. 

    Django ImageField and saving them was surprisingly tricky.
    Django ImageFields are really just path-string relative to one's
    project's MEDIA_ROOT. The ImageField's save function actually builds
    this path from the filename, and its the path defined in the 
    upload_to= keyword argument.

    In self.image.save the last parameter, saveFalse, is very important. 
    If save=True which it defaults to, then self.image.save will try to 
    call the models save method  which will call itself infinitely and 
    save copies of the image to disk until Disk Full.
    To fix this problem, just set save=False and then make sure to call 
    the next line at some point afterwards so the model is saved to the 
    database.
    """
    title = models.CharField(max_length=60, blank=True, null=True)
    image = models.ImageField(upload_to="images/")  
    thumbnail = models.ImageField(upload_to="images/", blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=50)
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(User, null=True, blank=True)
    thumbnail2 = models.ImageField(upload_to="images/", blank=True, null=True)

    def save(self, *args, **kwargs):
        #overriding model save method by PIL for saving image dimentions, orientation by reading exif. 
        #(Exchangeable image file format - http://en.wikipedia.org/wiki/Exchangeable_image_file_format
        super(Image, self).save(*args, **kwargs)
        im = PImage.open(pjoin(settings.MEDIA_ROOT, self.image.name))
        if hasattr(im, '_getexif'):
            orientation = 0x0112 #orientation key 
            exif = im._getexif()
            if exif is not None:
                if orientation in exif:
                    orientation = exif[orientation]
                    rotations = { 
                        3: PImage.ROTATE_180,
                        6: PImage.ROTATE_270,
                        8: PImage.ROTATE_90
                    }   
                    if orientation in rotations:
                        im = im.transpose(rotations[orientation])
                        im.save(self.image.path, overwrite=True)
                    
        im = PImage.open(pjoin(settings.MEDIA_ROOT, self.image.name))
        self.width, self.height = im.size
        
        # large thumbnail to show it in front page
        fn, ext = os.path.splitext(self.image.name)
        im.thumbnail((128,128), PImage.ANTIALIAS)
        thumb_fn = fn + "-thumb2" + ext
        tf2 = NamedTemporaryFile()
        im.save(tf2.name, "JPEG", overwrite=True)
        filename = './media/' + thumb_fn
        try:
            os.remove(filename)
        except OSError:
            pass
        self.thumbnail2.save(thumb_fn, File(open(tf2.name)), save=False)
        tf2.close()

        # small thumbnail for admin view 
        im.thumbnail((40,40), PImage.ANTIALIAS)
        thumb_fn = fn + "-thumb" + ext
        tf = NamedTemporaryFile()
        im.save(tf.name, "JPEG",  overwrite=True)
        filename = './media/' + thumb_fn
        try:
            os.remove(filename)
        except OSError:
            pass
        self.thumbnail.save(thumb_fn, File(open(tf.name)), save=False)
        tf.close()
        
        super(Image, self).save(*args, ** kwargs)


    def size(self):
        """Image size."""
        return "%s x %s" % (self.width, self.height)

    def __unicode__(self):
        return self.image.name

    def tags_(self):
        lst = [x[1] for x in self.tags.values_list()]
        return str(join(lst, ', '))

    def albums_(self):
        album_obj = Album.objects.filter(pics = self)
        lst = [p.title for p in album_obj]
        return str(join(lst, ', '))

    def thumbnail_(self):
        return """<a href="/media/%s"><img border="0" alt="" src="/media/%s" /></a>""" % (
                (self.image.name, self.thumbnail.name))
    thumbnail_.allow_tags = True

    #order by recent first
    class Meta:
        ordering = ['-created',]
        
        
class Album(models.Model):
    """Album is the container for images. It has many to many 
    relation with Image, an image can exist in multipe albums"""
    title = models.CharField(max_length=60)
    user = models.ForeignKey(User, null=True, blank=True)
    description = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)    
    public = models.BooleanField(default=False)
    pics = models.ManyToManyField(Image, blank=True)
    
    def __unicode__(self):
        return self.title
    
    def images(self):
        lst = [x.image.name for x in self.pics.all()]
        lst = ["<a href='/media/%s'>%s</a>" % (x, x.split('/')[-1]) for x in lst]
        return join(lst, ', ')
    images.allow_tags = True

    #Order by recent first
    class Meta:
        ordering = ['-created_date',]
        
        
