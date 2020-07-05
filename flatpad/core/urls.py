from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("get_presence", views.get_presence, name="get_presence"),
    path("update_presence", views.update_presence, name="update_presence"),
    path("submit_pad", views.submit_pad, name="submit_pad"),
]
