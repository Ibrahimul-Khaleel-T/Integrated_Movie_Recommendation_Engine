"""
URL configuration for scene_it project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from users import views as users_view
from django.conf import settings
from django.conf.urls.static import static
from movies import views as movies_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',users_view.index,name='index'),
    path('signin',users_view.signin,name='signin'),
    path('signup',users_view.signup,name='signup'),
    path('reset_password',users_view.password_reset_request,name='reset_password'),
    path('verify_otp',users_view.verify_otp,name='verify_otp'),
    path('set_new_password',users_view.set_new_password,name='set_new_password'),
    path('dp',users_view.dp,name='dp'),
    path('user_home_page',movies_view.user_home_page,name='user_home_page'),
    path('user_profile',users_view.user_profile,name='user_profile'),
    path('signout',users_view.signout,name='signout'),
    path('edit_user_profile',users_view.edit_user_profile,name='edit_user_profile'),
    path('submit_review',movies_view.submit_review,name='submit_review'),
    path('movie_rating_list',movies_view.movie_rating_list,name='movie_rating_list'),
    path('recommend', movies_view.combined_recommendations, name='combined_recommendations'),
    path('language/<str:lang_code>',movies_view.movies_by_language,name='movies_by_language'),
    path('genre/<str:genre_name>',movies_view.movies_by_genre,name='movies_by_genre'),
    path('search/',movies_view.search_movies,name='search_movies'),
    path('submit_contact',users_view.submit_contact,name='submit_contact'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

