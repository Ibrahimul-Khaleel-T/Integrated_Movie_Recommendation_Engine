from django.shortcuts import render,redirect
from django.http import HttpResponse
from users.models import UserInfo
from django.contrib import messages
import random,requests,json
from .models import Review
from django.contrib.auth.decorators import login_required
API_KEY="830596140937bda925ac2c89f6deb604"

# Create your views here.

def fetch_top_rated_movies(language_code):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_original_language={language_code}&sort_by=popularity.desc&page=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch movies for {language_code}: {e}")
        return [] 


def get_movie_credits(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        credits = response.json()
        director = next((member['name'] for member in credits['crew'] if member['job'] == 'Director'), 'N/A')
        return director
    except:
        return 'N/A'


def fetch_genres():
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={API_KEY}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        genres = response.json().get('genres', [])
        return {genre['id']: genre['name'] for genre in genres}
    except:
        return {}
    

def user_home_page(request):
    languages = ['en', 'hi', 'ml', 'ta', 'te', 'kn', 'ja', 'es']
    seen_titles = set()
    unique_movies = []

    genre_map = fetch_genres()

    for lang_code in languages:
        movies = fetch_top_rated_movies(lang_code)
        for movie in movies:
            if movie['title'] not in seen_titles:
                seen_titles.add(movie['title'])
                movie['director'] = get_movie_credits(movie['id'])
                movie['genres'] = [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
                movie['trailer_key'] = get_movie_trailer_key(movie['id'])
                movie['json'] = json.dumps({**movie,"director": movie['director'],"genres": movie['genres'],"trailer_key": movie['trailer_key'], })

                unique_movies.append(movie)

    return render(request, 'user_home_page.html', {'movies': unique_movies})


def get_movie_trailer_key(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        videos = response.json().get('results', [])

        # Prioritize YouTube trailer
        for video in videos:
            if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                return video['key']
        
        # If no "Trailer", try a "Teaser" from YouTube
        for video in videos:
            if video['type'] == 'Teaser' and video['site'] == 'YouTube':
                return video['key']

        # Try first YouTube video as fallback
        for video in videos:
            if video['site'] == 'YouTube':
                return video['key']

        return None
    except Exception as e:
        print(f"Error fetching trailer for {movie_id}: {e}")
        return None
    

@login_required
def submit_review(request):
    if request.method=="POST":
        movie_id=request.POST.get("movie_id")
        rating=int(request.POST.get("rating"))
        comment=request.POST.get("comment")
        from django.shortcuts import render,redirect
from django.http import HttpResponse
from users.models import UserInfo
from django.contrib import messages
import random,requests,json
from .models import Review
from django.contrib.auth.decorators import login_required
API_KEY="830596140937bda925ac2c89f6deb604"

# Create your views here.

def fetch_top_rated_movies(language_code):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_original_language={language_code}&sort_by=popularity.desc&page=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch movies for {language_code}: {e}")
        return [] 


def get_movie_credits(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        credits = response.json()
        director = next((member['name'] for member in credits['crew'] if member['job'] == 'Director'), 'N/A')
        return director
    except:
        return 'N/A'


def fetch_genres():
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={API_KEY}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        genres = response.json().get('genres', [])
        return {genre['id']: genre['name'] for genre in genres}
    except:
        return {}
    

def user_home_page(request):
    languages = ['en', 'hi', 'ml', 'ta', 'te', 'kn', 'ja', 'es']
    seen_titles = set()
    unique_movies = []

    genre_map = fetch_genres()

    for lang_code in languages:
        movies = fetch_top_rated_movies(lang_code)
        for movie in movies:
            if movie['title'] not in seen_titles:
                seen_titles.add(movie['title'])
                movie['director'] = get_movie_credits(movie['id'])
                movie['genres'] = [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
                movie['trailer_key'] = get_movie_trailer_key(movie['id'])
                movie['json'] = json.dumps({**movie,"director": movie['director'],"genres": movie['genres'],"trailer_key": movie['trailer_key'], })

                unique_movies.append(movie)

    return render(request, 'user_home_page.html', {'movies': unique_movies})


def get_movie_trailer_key(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        videos = response.json().get('results', [])

        # Prioritize YouTube trailer
        for video in videos:
            if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                return video['key']
        
        # If no "Trailer", try a "Teaser" from YouTube
        for video in videos:
            if video['type'] == 'Teaser' and video['site'] == 'YouTube':
                return video['key']

        # Try first YouTube video as fallback
        for video in videos:
            if video['site'] == 'YouTube':
                return video['key']

        return None
    except Exception as e:
        print(f"Error fetching trailer for {movie_id}: {e}")
        return None
    

@login_required
def submit_review(request):
    if request.method=="POST":
        movie_id=request.POST.get("movie_id")
        rating=int(request.POST.get("rating"))
        comment=request.POST.get("comment")
        movieTitle=movie_id['title']
        from django.shortcuts import render,redirect
from django.http import HttpResponse
from users.models import UserInfo
from django.contrib import messages
import random,requests,json
from .models import Review
from django.contrib.auth.decorators import login_required
API_KEY="830596140937bda925ac2c89f6deb604"

# Create your views here.

def fetch_top_rated_movies(language_code):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_original_language={language_code}&sort_by=popularity.desc&page=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch movies for {language_code}: {e}")
        return [] 


def get_movie_credits(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        credits = response.json()
        director = next((member['name'] for member in credits['crew'] if member['job'] == 'Director'), 'N/A')
        return director
    except:
        return 'N/A'


def fetch_genres():
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={API_KEY}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        genres = response.json().get('genres', [])
        return {genre['id']: genre['name'] for genre in genres}
    except:
        return {}
    

def user_home_page(request):
    languages = ['en', 'hi', 'ml', 'ta', 'te', 'kn', 'ja', 'es']
    seen_titles = set()
    unique_movies = []

    genre_map = fetch_genres()

    for lang_code in languages:
        movies = fetch_top_rated_movies(lang_code)
        for movie in movies:
            if movie['title'] not in seen_titles:
                seen_titles.add(movie['title'])
                movie['director'] = get_movie_credits(movie['id'])
                movie['genres'] = [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
                movie['trailer_key'] = get_movie_trailer_key(movie['id'])
                movie['json'] = json.dumps({**movie,"director": movie['director'],"genres": movie['genres'],"trailer_key": movie['trailer_key'], })

                unique_movies.append(movie)

    return render(request, 'user_home_page.html', {'movies': unique_movies})


def get_movie_trailer_key(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        videos = response.json().get('results', [])

        # Prioritize YouTube trailer
        for video in videos:
            if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                return video['key']
        
        # If no "Trailer", try a "Teaser" from YouTube
        for video in videos:
            if video['type'] == 'Teaser' and video['site'] == 'YouTube':
                return video['key']

        # Try first YouTube video as fallback
        for video in videos:
            if video['site'] == 'YouTube':
                return video['key']

        return None
    except Exception as e:
        print(f"Error fetching trailer for {movie_id}: {e}")
        return None
    

@login_required
def submit_review(request):
    if request.method == "POST":
        movie_id = request.POST.get("movie_id")
        rating = int(request.POST.get("rating"))
        comment = request.POST.get("comment")
        movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
        try:
            response = requests.get(movie_url, timeout=10)
            response.raise_for_status()
            movie_data = response.json()
            movieTitle = movie_data.get('title', 'Unknown')
        except:
            movieTitle = 'Unknown'

        Review.objects.create(user=request.user,movie_id=movie_id,rating=rating,comment=comment)
        messages.success(request, f"Your review for '{movieTitle}' was submitted.")
        return redirect(request.META.get('HTTP_REFERER', '/'))
    

@login_required
def movie_rating_list(request):
    user = request.user
    reviews = Review.objects.filter(user=user)

    rated_movies = []
    for review in reviews:
        try:
            tmdb_url = f"https://api.themoviedb.org/3/movie/{review.movie_id}?api_key={API_KEY}&language=en-US"
            response = requests.get(tmdb_url, timeout=5) 
            response.raise_for_status()  
            movie_data = response.json()
            director = get_movie_credits(review.movie_id)

            rated_movies.append({
                "movie": {"id": review.movie_id,"title": movie_data.get("title"),"poster_path": movie_data.get("poster_path"),"director": director,"year":movie_data.get("release_date"),"overview": movie_data.get("overview"),},
                "review": {"rating": review.rating,"comment": review.comment,"created_at": review.created_at,}})
        except Exception as e:
            print(f"Error fetching movie {review.movie_id}: {e}")
            rated_movies.append({
                "movie": {"id": review.movie_id,"title": "Movie not found","poster_path": None,"director": "Not found","year":"Not found","overview": "",},
                "review": {"rating": review.rating,"comment": review.comment,"created_at": review.created_at,}})
    return render(request, 'movie_rating_list.html', {'rated_movies': rated_movies})