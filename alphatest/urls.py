from django.urls import path
from . import views

app_name = "alphatest"
urlpatterns = [
    path("", views.index, name = "index"),
    path("hint/<str:hint>/", views.index, name = "index"),
    path("ask/", views.ask, name = "ask"),
    path("request_hint/", views.request_hint, name = "hint"),
    path("next_word/", views.next_word, name = "next_word"),
]
