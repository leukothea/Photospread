from django.contrib import admin
from photo.models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

#3rd party file uploader app 
from multiupload.admin import MultiUploadAdmin

class AlbumInline(admin.TabularInline):
    # Inlining with many-to-many relationships (Optional-Todo)
    model = Album.pics.through

class TagAdmin(admin.ModelAdmin):
    list_display = ["tag"]

class ImageAdmin(admin.ModelAdmin):
    """ Admin interface for both users and superuser for photos.
    Depending on the access rights restrict the permissions by 
    overriding standard methods. """
    #inlines = [ AlbumInline, ]
    list_display = ["__unicode__", "title", "user", "albums_", 
                    "rating", "size", "tags_", "thumbnail_", "created"]
    list_filter = ["tags", "user"]

    #Override the admin form to show(/not to show) user @admin interface
    # Admin can view different users , User can see only self
    def get_form(self, request, obj=None, **kwargs):
        if not request.user.is_superuser:
            kwargs['exclude'] = ['user',]
        return super(ImageAdmin, self).get_form(request, obj, **kwargs)

    def has_change_permission(self, request, obj=None):
        has_class_permission = super(ImageAdmin, self).has_change_permission(request, obj)
        if not has_class_permission:
            return False
        if obj is not None and not request.user.is_superuser and request.user.id != obj.user.id:
            return False
        return True
    
    #user can view only his/her images, Super user (admin) has full permissions 
    def queryset(self, request):
        if request.user.is_superuser:
            return Image.objects.all()
        return Image.objects.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.user: obj.user = request.user
        obj.save()


class AlbumAdmin(MultiUploadAdmin):
    """ 
    1) Admin interface for both users and superuser for albums.
    Depending on the access rights restrict the permissions by 
    overriding standard methods. 
    2) Allow upload multiple photos inside an album using 
    multiuploader app.
    """
    search_fields = ["title"]

    def get_form(self, request, obj=None, **kwargs):
        if not request.user.is_superuser:
            kwargs['exclude'] = ['user',]
        return super(AlbumAdmin, self).get_form(request, obj, **kwargs)
   
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "pics" and not request.user.is_superuser:
            kwargs["queryset"] = Image.objects.filter(user=request.user)
        return super(AlbumAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
 
    def has_change_permission(self, request, obj=None):
        has_class_permission = super(AlbumAdmin, self).has_change_permission(request, obj)
        if not has_class_permission:
            return False
        if obj is not None and not request.user.is_superuser and request.user.id != obj.user.id:
            return False
        return True

    def queryset(self, request):
        if request.user.is_superuser:
            return Album.objects.all()
        return Album.objects.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.user: obj.user = request.user
        obj.save()

    # default value of multiupload parameters:
    #change_form_template = 'multiupload/change_form.html'
    #change_list_template = 'multiupload/change_list.html'
    #multiupload_template = 'multiupload/upload.html'
    # if true, enable multiupload on list screen
    # generaly used when the model is the uploaded element
    multiupload_list = False
    # if true enable multiupload on edit screen
    # generaly used when the model is a container for uploaded files
    # eg: gallery
    # can upload files direct inside a gallery.
    multiupload_form = True
    # max allowed filesize for uploads in bytes
    multiupload_maxfilesize = 8 * 2 ** 20 #8MB
    # min allowed filesize for uploads in bytes
    multiupload_minfilesize = 0
    # tuple with mimetype accepted
    multiupload_acceptedformats = ( "image/jpeg",
                                    "image/pjpeg",
                                    "image/png",)

    def process_uploaded_file(self, uploaded, object, request):
        """
        This method will be called for every file uploaded.
        Parameters:
            :uploaded: instance of uploaded file
            :object: instance of object if in form_multiupload else None
            :kwargs: request.POST received with file
        Return:
            It MUST return at least a dict with:
            {
                'url': 'url to download the file',
                'thumbnail_url': 'some url for an image_thumbnail or icon',
                'id': 'id of instance created in this method',
                'name': 'the name of created file',
            }
        """
        title = request.POST.get('title', '') or uploaded.name
        temp = Image(image=uploaded, title=title, user=request.user)
        temp.save()
        object.pics.add(temp)
        object.save()
        return {
            'url': temp.thumbnail_(),
            'thumbnail_url': temp.thumbnail_(),
            'id': temp.id,
            'name': temp.title
        }

    def delete_file(self, pk, request):
        """
        Function to delete a file.
        Not really meaningful to delete the file(s) here
        Just keeping the function to extend in future.
        """
        obj = get_object_or_404(self.queryset(request), pk=pk)
        obj.delete()

#Register models with admin
admin.site.register(Album, AlbumAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Image, ImageAdmin)
