from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.conf import settings
from photo.models import *
from string import join
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.db.models import Q

#Photo-upload to FB, smugmug (a 3rd party snippets)
import fbconsole as fb
from photo.smugmug import *

ALBUMS_PER_PAGE = 4

def homepage(request):
    """ Home page listing.
    It lists all public albums and user albums if logged in 
    Supports pagination (Number of albums per page)
    """
    albums = Album.objects.all()
    if request.user.is_authenticated():
        albums = albums.filter(Q(public=True) | Q(user=request.user))
    else:
        albums = albums.filter(public=True)
    
    # Number of albums per page 
    paginator = Paginator(albums, ALBUMS_PER_PAGE) 
    try: page = int(request.GET.get("page", '1'))
    except ValueError: page = 1

    try:
        albums = paginator.page(page)
    except (InvalidPage, EmptyPage):
        albums = paginator.page(paginator.num_pages)

    for album in albums.object_list:
        # Number of images per album in the front view 
        album.images = album.pics.all()[:4]

    return render_to_response("photo/list.html", dict(albums=albums, user=request.user,
        media_url=settings.MEDIA_URL))


def my_albums(request):
    """ My album(s) listing.
    It lists all user-albums if logged in.
    """
    albums = Album.objects.all()
    if request.user.is_authenticated():
        albums = albums.filter(user=request.user)
    else:
        raise Http404 
    # Number of albums per page 
    paginator = Paginator(albums, ALBUMS_PER_PAGE) 
    try: page = int(request.GET.get("page", '1'))
    except ValueError: page = 1 

    try:
        albums = paginator.page(page)
    except (InvalidPage, EmptyPage):
        albums = paginator.page(paginator.num_pages)

    for album in albums.object_list:
        # Number of images per album in the front view 
        album.images = album.pics.all()[:4]

    return render_to_response("photo/list.html", dict(albums=albums, user=request.user,
        media_url=settings.MEDIA_URL))


def album(request, pk, view="thumbnails"):
    """Individual album listing.
    It support 3 views:
    1) Thumbnail(default)
    2) Full (stacked images / alternate to slide show)
    3) Update (Edit image fileds) """

    num_images = 30
    if view == "full": num_images = 10
    
    album = Album.objects.get(pk=pk)
    if((album.public == False) and ( not (album.user == request.user))):
        raise Http404
    images = album.pics.all()
    paginator = Paginator(images, num_images)
    try: page = int(request.GET.get("page", '1'))
    except ValueError: page = 1

    try:
        images = paginator.page(page)
    except (InvalidPage, EmptyPage):
        images = paginator.page(paginator.num_pages)
    
    # add list of tags as string and list of album objects to each image object
    for img in images.object_list:
        tags = [x[1] for x in img.tags.values_list()]
        img.tag_lst = join(tags, ', ')
        album_obj = Album.objects.filter(pics = img)
        img.album_lst = [p.title for p in album_obj]       

    if (album.user == request.user):        
        d = dict(album=album, images=images, user=request.user, view=view, 
                albums=Album.objects.filter(user=request.user),
                media_url=settings.MEDIA_URL)
    else:
        d = dict(album=album, images=images, user=request.user, view=view, 
                albums=Album.objects.filter(public=True),
                media_url=settings.MEDIA_URL)
    d.update(csrf(request))
    return render_to_response("photo/album.html", d)


def image(request, pk):
    """Individual Image page."""
    img = Image.objects.get(pk=pk)
    return render_to_response("photo/image.html", dict(image=img, user=request.user,
         backurl=request.META["HTTP_REFERER"], media_url=settings.MEDIA_URL))

def update(request):
    """Update image title, rating, tags, albums 
    (Album's edit view) """
    p = request.POST
    images = defaultdict(dict)

    # create dictionary of properties for each image
    for k, v in p.items():
        if k.startswith("title") or k.startswith("rating") or k.startswith("tags"):
            k, pk = k.split('-')
            images[pk][k] = v
        elif k.startswith("album"):
            pk = k.split('-')[1]
            images[pk]["albums"] = p.getlist(k)

    #for performance reasons, rather than setting a property at a time and saving,
    # process properties, assign to image objects and save.
    for k, d in images.items():
        image = Image.objects.get(pk=k)
        image.title = d["title"]
        image.rating = int(d["rating"])

        # tags - assign or create if a new tag!
        #(the function returns a tuple where second value indicates if a new object was created; 
        #we’re only interested in the object itself in this case).
        lst = []
        for t in tags:
            if t: lst.append(Tag.objects.get_or_create(tag=t)[0])
        image.tags = lst
        image.save()            
 
        if "albums" in d:
            a = Album.objects.filter(pics = image)
            for m in a: 
                m.pics.remove(image)
                m.save()
            for x in d["albums"] : 
                alb   = Album.objects.get(pk=x)
                alb.pics.add(image)
                alb.save()
    return HttpResponseRedirect(request.META["HTTP_REFERER"], dict(media_url=settings.MEDIA_URL))


@login_required
def search(request):
    """Search, filter, sort images based on different parameters.
    The form can have a large number of parameters that are submitted via POST request, 
    while the paginator works through a link which is a GET request. 
    So save them in session. When you submit the form, the view will save all parameters 
    in session dictionary, filter the results and show you the first page. 
    Once you click on the second page, parameters are loaded from session. 
    If you resubmit the form, you will go back to the first page again.
    """
    try: page = int(request.GET.get("page", '1'))
    except ValueError: page = 1 

    p = request.POST
    images = defaultdict(dict)

    # init parameters
    parameters = {}
    keys = ("title filename rating_from rating_to width_from width_to height_from height_to tags view"
        " user sort asc_desc").split()
    for k in keys:
        parameters[k] = ''
    parameters["album"] = []

    # create dictionary of properties for each image and a dict of search/filter parameters
    for k, v in p.items():
        if k == "album":
            parameters[k] = [int(x) for x in p.getlist(k)]
        elif k == "user":
            if v != "all": v = int(v)
            parameters[k] = v 
        elif k in parameters:
            parameters[k] = v 
        elif k.startswith("title") or k.startswith("rating") or k.startswith("tags"):
            k, pk = k.split('-')
            images[pk][k] = v 
        elif k.startswith("album"):
            pk = k.split('-')[1]
            images[pk]["albums"] = p.getlist(k)

    # save or restore parameters from session
    if page != 1 and "parameters" in request.session:
        parameters = request.session["parameters"]
    else:
        request.session["parameters"] = parameters

    results = update_and_filter(request, images, parameters)

    # make paginator
    paginator = Paginator(results, 20)
    try:
        results = paginator.page(page)
    except (InvalidPage, EmptyPage):
        request = paginator.page(paginator.num_pages)

    # add list of tags as string and list of album names to each image object
    for img in results.object_list:
        tags = [x[1] for x in img.tags.values_list()]
        img.tag_lst = join(tags, ', ')
        album_obj = Album.objects.filter(pics = img)
        img.album_lst = [p.title for p in album_obj]

    d = dict(results=results, user=request.user, albums=Album.objects.filter(user=request.user), prm=parameters,
             users=User.objects.all(), media_url=settings.MEDIA_URL)
    d.update(csrf(request))
    return render_to_response("photo/search.html", d)


def update_and_filter(request, images, p):
    """Update image data if changed, filter results 
    through parameters and return results list."""
    # process properties, assign to image objects and save
    for k, d in images.items():
        image = Image.objects.get(pk=k)
        
        image.title = d["title"]
        image.rating = int(d["rating"])

        # tags - assign or create if a new tag!
        tags = d["tags"].split(', ')
        lst = []
        for t in tags:
            if t: lst.append(Tag.objects.get_or_create(tag=t)[0])
        image.tags = lst
        image.save()
        
        #This is used to update to which album(/s) the image belongs to.
        if "albums" in d:
            a = Album.objects.filter(pics = image)
            for m in a:  
                m.pics.remove(image)
                m.save()
            for x in d["albums"] : 
                alb   = Album.objects.get(pk=x)
                alb.pics.add(image)
                alb.save()

    # sort and filter results by parameters
    order = "created"
    if p["sort"]: order = p["sort"]
    if p["asc_desc"] == "desc": order = '-' + order

    imgl = Album.objects.none() 
    if p["album"]:
        for n in p["album"]:
            a = Album.objects.get(pk=n)
            img_l = a.pics.all()
            #Combining query sets - note its not a list
            imgl = imgl | img_l
    else:
        #Combining queries based on user albums and public albums
        for al in Album.objects.filter(Q(public=True) | Q(user=request.user)):
            img_l = al.pics.all()
            imgl = imgl | img_l

    results = imgl.order_by(order)
    if p["title"]       : results = results.filter(title__icontains=p["title"])
    if p["filename"]    : results = results.filter(image__icontains=p["filename"])
    if p["rating_from"] : results = results.filter(rating__gte=int(p["rating_from"]))
    if p["rating_to"]   : results = results.filter(rating__lte=int(p["rating_to"]))
    if p["width_from"]  : results = results.filter(width__gte=int(p["width_from"]))
    if p["width_to"]    : results = results.filter(width__lte=int(p["width_to"]))
    if p["height_from"] : results = results.filter(height__gte=int(p["height_from"]))
    if p["height_to"]   : results = results.filter(height__lte=int(p["height_to"]))
    if p["user"] and p["user"] != "all"    : results = results.filter(user__pk=int(p["user"]))

    if p["tags"]:
        tags = p["tags"].split(', ')
        lst = []
        for t in tags:
            if t:
                tgs = Tag.objects.filter(tag=t)
                if tgs:
                    results = results.filter(tags=tgs[0])
                else:
                    results = []
    if results:
        #distinct() method to avoid duplicate
        results = results.distinct()
    return results


def upload(request, post_pk, pk=None):
    """ Upload selected images to Facebook or Smugmug """
    if not pk: pklst = request.POST.getlist("checked")
    else: pklst = [pk]

    image_dict = {}
    for pk in pklst:
        img = Image.objects.get(pk=pk)
        img_path = str("./media/" + img.image.name)
        image_dict[img] = img_path
    
    if "_fb" in request.POST:

        for k,v in image_dict.items():
            fb.authenticate() 
            try:
                fb.graph_post("/me/photos", {"message":str(k.title), "source":open(v)})
            except:
                # Upload failed, as access token was expired
                # delete and retry 
                os.remove(fb.LOCAL_FILE)
                fb.authenticate()
                try:
                    fb.graph_post("/me/photos", {"message":str(k.title), "source":open(v)})
                except:
                    pass

    elif "_sm" in request.POST:
        smug = SmugmugClient()
        login_info = smug.login('smugmug.login.withPassword')
        #album_name = raw_input('Name of album to upload to: ') 
        # todo @linh: how get a pop up message to ask user which album to upload to in views.py
        session = login_info['Login']['Session']['id']
        # album_id = smug.getalbumid(session, album_name) 
        # comment out to just assign a known album_id for testing integration within django
        album_id = 38487135 # a known existing album_id for testing. http://linhchan.smugmug.com/Testing/
        for v in image_dict.values():
            smug.uploadtoalbum(v,session,album_id)
        # todo @linh: Add pop-up message to confirm success or failure

    return HttpResponseRedirect(request.META["HTTP_REFERER"], dict(media_url=settings.MEDIA_URL))

