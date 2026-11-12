from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "eGrocery Admin"
admin.site.site_title = "eGrocery Admin"
admin.site.index_title = "Store management"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
]

# Serve uploaded product images. Fine for small shops; for big traffic move
# media to cloud storage (S3, Cloudinary...) and set SERVE_MEDIA=False.
if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
