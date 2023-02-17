from django.urls import path
from manufacturing.api.views import *

urlpatterns = [
    path("customfields", CustomFields.as_view(), name="CustomFields")
]