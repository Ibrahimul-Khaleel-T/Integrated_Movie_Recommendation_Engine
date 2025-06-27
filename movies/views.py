from django.shortcuts import render,redirect
from django.http import HttpResponse
from users.models import UserInfo
from django.contrib import messages
import random,requests,json
from .models import Review
from django.contrib.auth.decorators import login_required
import pandas as pd
from surprise import Dataset,Reader,SVD
from surprise.model_selection import train_test_split
from requests.exceptions import RequestException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
API_KEY="830596140937bda925ac2c89f6deb604"

# Create your views here.  

def fetch_top_rated_movies(language_code):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_original_language={language_code}&sort_by=popularity.desc&page=3"
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

#Collaborative Filtering

def get_ratings_df():
    reviews = Review.objects.all().values('user_id', 'movie_id', 'rating')
    return pd.DataFrame(reviews)


def train_svd_model():
    df=get_ratings_df()
    reader=Reader(rating_scale=(1,5))
    data=Dataset.load_from_df(df[['user_id','movie_id','rating']],reader)

    trainset=data.build_full_trainset()
    model=SVD()
    model.fit(trainset)

    return model


def get_recommendations_for_user(user_id, model, top_n=20):
    # Get all movie_ids the user hasn't rated yet
    df = get_ratings_df()
    rated_movies = df[df['user_id'] == user_id]['movie_id'].tolist()
    all_movies = df['movie_id'].unique()

    unrated_movies = [mid for mid in all_movies if mid not in rated_movies]

    predictions = []
    for movie_id in unrated_movies:
        pred = model.predict(user_id, movie_id)
        predictions.append((movie_id, pred.est))

    predictions.sort(key=lambda x: x[1], reverse=True)
    top_movie_ids = [movie_id for movie_id, _ in predictions[:top_n]]
    return top_movie_ids


def fetch_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print(f"Error fetching movie ID {movie_id}: {e}")
        return None



# @login_required
# def movie_recommendations(request):
#     user_id = request.user.id
#     model = train_svd_model()
#     recommended_ids = get_recommendations_for_user(user_id, model)

#     # print("Recommended Movie IDs:", recommended_ids)  # Add this

#     recommended_movies = [fetch_movie_details(mid) for mid in recommended_ids]
#     recommended_movies = [movie for movie in recommended_movies if movie]

#     # print("Recommended Movie Data:", recommended_movies)  # And this
#     for movie in recommended_movies:
#         genre_map = fetch_genres()
#         movie_data = {
#             "id": movie.get('id'),
#             "title": movie.get('title'),
#             "overview": movie.get('overview', ''),
#             "release_date": movie.get('release_date', ''),
#             "poster_path": movie.get('poster_path', ''),
#             "backdrop_path": movie.get('backdrop_path', ''),
#             "director": get_movie_credits(movie['id']),
#             "genres": [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])],
#             "trailer_key": get_movie_trailer_key(movie['id']),
#         }
#         movie['json'] = json.dumps(movie_data)


#     return render(request, 'recommendations.html', {'recommended_movies': recommended_movies})


#content filtering

def get_popular_movie_ids_from_tmdb(languages=['en', 'hi', 'ml'], limit_per_lang=30):
    all_movie_ids = set()

    for lang in languages:
        movies = fetch_top_rated_movies(lang)
        for movie in movies[:limit_per_lang]:  
            all_movie_ids.add(movie['id'])

    return list(all_movie_ids)



def fetch_movie_text(movie_id):
    base_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    
    try:
        # ✅ 1. Fetch main movie data (overview, tagline, genres)
        url = f"{base_url}?api_key={API_KEY}&language=en-US"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        overview = data.get('overview', '')
        tagline = data.get('tagline', '')
        genres = ' '.join([genre['name'] for genre in data.get('genres', [])])

        # ✅ 2. Fetch cast and crew
        credits_url = f"{base_url}/credits?api_key={API_KEY}"
        credits_resp = requests.get(credits_url, timeout=5)
        credits_resp.raise_for_status()
        credits_data = credits_resp.json()

        top_cast = [cast['name'] for cast in credits_data.get('cast', [])[:5]]
        cast_str = ' '.join(top_cast)

        directors = [crew['name'] for crew in credits_data.get('crew', []) if crew['job'] == 'Director']
        director_str = ' '.join(directors)

        # ✅ 3. Fetch keywords
        keywords_url = f"{base_url}/keywords?api_key={API_KEY}"
        kw_resp = requests.get(keywords_url, timeout=5)
        kw_resp.raise_for_status()
        keywords = [kw['name'] for kw in kw_resp.json().get('keywords', [])]
        keywords_str = ' '.join(keywords)

        # ✅ 4. Combine all text into a single string
        full_text = ' '.join([overview, tagline, genres, cast_str, director_str, keywords_str])
        return full_text.strip()
    
    except requests.RequestException as e:
        print(f"[ERROR] fetch_movie_text failed for movie_id={movie_id}: {e}")
        return ''



def get_movie_tfid_matrix(movie_ids):
    movie_texts = []
    movie_id_list = []

    for mid in movie_ids:
        text = fetch_movie_text(mid)
        if text:
            movie_texts.append(text)
            movie_id_list.append(mid)
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(movie_texts)

    return movie_id_list, tfidf_matrix



def recommend_similar_movies(movie_id, movie_id_list, cosine_sim ,top_n=10):
    try:
        idx = movie_id_list.index(movie_id)
    except ValueError:
        return []
    
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    print("[DEBUG] Top similarity scores:", sim_scores[:10])
    sim_scores = sim_scores[1:top_n+1]

    recommend_ids = [movie_id_list[i[0]] for i in sim_scores]
    return recommend_ids


@login_required
def combined_recommendations(request):
    user_id = request.user.id

    # ✅ 1. Collaborative Filtering (SVD)
    model = train_svd_model()
    collaborative_ids = get_recommendations_for_user(user_id, model)
    collaborative_movies = [fetch_movie_details(mid) for mid in collaborative_ids]
    collaborative_movies = [movie for movie in collaborative_movies if movie]

    for movie in collaborative_movies:
        genre_map = fetch_genres()
        movie_data = {
            "id": movie.get('id'),
            "title": movie.get('title'),
            "overview": movie.get('overview', ''),
            "release_date": movie.get('release_date', ''),
            "poster_path": movie.get('poster_path', ''),
            "backdrop_path": movie.get('backdrop_path', ''),
            "director": get_movie_credits(movie['id']),
            "genres": [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])],
            "trailer_key": get_movie_trailer_key(movie['id']),
        }
        movie['json'] = json.dumps(movie_data)

    # ✅ 2. Content-Based Filtering (TF-IDF)
    content_movies = []
    movie_id = None  # Define early so it's available in the template

    # Get base movie ID from user's last review
    last_review = Review.objects.filter(user_id=user_id).order_by('-id').first()
    if last_review:
        movie_id = last_review.movie_id
        movie_ids = get_popular_movie_ids_from_tmdb(languages=['en', 'hi', 'ml', 'ta', 'te', 'kn', 'ja', 'es'], limit_per_lang=5)
        if movie_id not in movie_ids:
            movie_ids.append(movie_id)
        try:
            movie_id_list, tfidf_matrix = get_movie_tfid_matrix(movie_ids)
            cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
            content_ids = recommend_similar_movies(movie_id, movie_id_list, cosine_sim)

            content_movies = [fetch_movie_details(mid) for mid in content_ids]
            content_movies = [movie for movie in content_movies if movie]
            genre_map = fetch_genres()

            for movie in content_movies:
                movie_data = {
                    "id": movie.get('id'),
                    "title": movie.get('title'),
                    "overview": movie.get('overview', ''),
                    "release_date": movie.get('release_date', ''),
                    "poster_path": movie.get('poster_path', ''),
                    "backdrop_path": movie.get('backdrop_path', ''),
                    "director": get_movie_credits(movie['id']),
                    "genres": [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])],
                    "trailer_key": get_movie_trailer_key(movie['id']),
                }
                movie['json'] = json.dumps(movie_data)

        except ValueError as e:
            return render(request, 'recommendations.html', {
                'collaborative_movies': collaborative_movies,
                'content_movies': [],
                'base_movie_id': movie_id,
                'message': 'Content-based recommendation failed: ' + str(e)
            })
    else:
        return render(request, 'recommendations.html', {
            'collaborative_movies': collaborative_movies,
            'content_movies': [],
            'base_movie_id': None,
            'message': 'You need to rate at least one movie for content-based recommendations.'
        })

    # ✅ Render both results to the same template
    return render(request, 'recommendations.html', {
        'collaborative_movies': collaborative_movies,
        'content_movies': content_movies,
        'base_movie_id': movie_id,
    })
