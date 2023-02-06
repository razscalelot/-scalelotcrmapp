from django.urls import path
from accounts.api.views import *

urlpatterns = [
    path('signup', SignUpUser.as_view(), name="SignUpUser"),
    path('signin', SignInUser.as_view(), name="SignInUser"),
]