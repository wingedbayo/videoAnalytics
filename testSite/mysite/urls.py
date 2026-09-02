from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "mysite"

urlpatterns = [
    path("", views.home, name="home"),
    path("chat-test/", views.chat_test, name="chat-test"),
    path("chat/<uuid:uuid>/", views.chat_history, name="chat"),
    path("logout/", views.logout, name="logout"),
] 
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)