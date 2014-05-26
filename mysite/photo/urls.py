from django.conf.urls import patterns, url 
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = patterns('photo.views',
    url(r'^$', 'homepage'),
    url(r'^myalbums/', 'my_albums'),
    url(r'^(\d+)/$', 'album'),
    url(r"^image/(\d+)/$", "image"),
    url(r"^(\d+)/(full|thumbnails|edit)/$", "album"),
    url(r"^update/$", "update"),
    url(r"^upload/(\d+)/$", "upload"),
    url(r"^search/$", "search"),
)
