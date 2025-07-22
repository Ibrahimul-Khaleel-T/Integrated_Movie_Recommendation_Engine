from django.shortcuts import render,redirect
from django.http import HttpResponse
from users.models import UserInfo
from django.contrib import messages
import random,requests,json,time
from .models import Review
from django.contrib.auth.decorators import login_required
import pandas as pd
from surprise import Dataset,Reader,SVD
from surprise.model_selection import train_test_split
from requests.exceptions import RequestException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
API_KEY="830596140937bda925ac2c89f6deb604"

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retries)
session.mount('https://', adapter)
session.mount('http://', adapter)

# Create your views here.  

def fetch_top_rated_movies(language_code):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_original_language={language_code}&sort_by=popularity.desc&page=3"
    try:
        time.sleep(0.3)
        response = session.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch movies for {language_code}: {e}")
        return [] 


def get_movie_credits(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}"
    try:
        time.sleep(0.3)  # ⏳ delay to avoid TMDB blocking
        response = session.get(url, timeout=5)
        response.raise_for_status()
        credits = response.json()
        director = next((member['name'] for member in credits['crew'] if member['job'] == 'Director'), 'N/A')
        return director
    except:
        return 'N/A'


def fetch_genres():
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={API_KEY}&language=en-US"
    try:
        time.sleep(0.3)  # ⏳ delay to avoid TMDB blocking
        response = session.get(url, timeout=5)
        response.raise_for_status()
        genres = response.json().get('genres', [])
        return {genre['id']: genre['name'] for genre in genres}
    except:
        return {}
    
    

def user_home_page(request):
    languages = ['en', 'hi', 'ml', 'ta', 'te', 'kn', 'es']
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
        time.sleep(0.3)  # ⏳ delay to avoid TMDB blocking
        response = session.get(url, timeout=5)
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
            time.sleep(0.3)  # ⏳ delay to avoid TMDB blocking
            response = session.get(movie_url, timeout=5)
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
            time.sleep(0.3)  # ⏳ delay to avoid TMDB blocking
            response = session.get(tmdb_url, timeout=5) 
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
        time.sleep(0.3)  # ⏳ delay to avoid TMDB blocking
        response = session.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print(f"Error fetching movie ID {movie_id}: {e}")
        return None




#content filtering

def get_popular_movie_ids_from_tmdb(languages=['en', 'hi', 'ml'], limit_per_lang=30):
    all_movie_ids = set()

    for lang in languages:
        movies = fetch_top_rated_movies(lang)
        for movie in movies[:limit_per_lang]:  
            all_movie_ids.add(movie['id'])

    return list(all_movie_ids)



# def fetch_movie_text(movie_id):
#     base_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
#     try:
#         # 1. Fetch main movie data
#         url = f"{base_url}?api_key={API_KEY}&language=en-US"
#         time.sleep(0.3)
#         response = session.get(url, timeout=5)
#         response.raise_for_status()
#         data = response.json()
        
#         overview = data.get('overview', '')
#         tagline = data.get('tagline', '')*20
#         genres = ' '.join([genre['name'] for genre in data.get('genres', [])])*20  # weight genres

#         # 2. Fetch keywords
#         keywords_url = f"{base_url}/keywords?api_key={API_KEY}"
#         kw_resp = session.get(keywords_url, timeout=5)
#         kw_resp.raise_for_status()
#         keywords = [kw['name'] for kw in kw_resp.json().get('keywords', [])]
#         keywords_str = ' '.join(keywords) * 20  # weight keywords

#         # 3. Combine
#         full_text = ' '.join([
#             overview,
#             tagline*10,
#             genres*10,
#             keywords_str
#         ])

#         return full_text.strip()
    
#     except requests.RequestException as e:
#         print(f"[ERROR] fetch_movie_text failed for movie_id={movie_id}: {e}")
#         return ''


def fetch_movie_text(movie_id):
    base_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    try:
        # 1. Fetch main movie data
        url = f"{base_url}?api_key={API_KEY}&language=en-US"
        time.sleep(0.3)
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        overview = data.get('overview', '')
        tagline = data.get('tagline', '')
        genres = [genre['name'] for genre in data.get('genres', [])]

        # 2. Fetch keywords
        keywords_url = f"{base_url}/keywords?api_key={API_KEY}"
        kw_resp = session.get(keywords_url, timeout=5)
        kw_resp.raise_for_status()
        keywords = [kw['name'] for kw in kw_resp.json().get('keywords', [])]

        # 3. Combine with controlled weights
        weighted_text = ' '.join([
            overview,
            (tagline + ' ') * 3,
            ' '.join(genres) * 3,
            ' '.join(keywords) * 4
        ])
        return weighted_text.strip()
    
    except requests.RequestException as e:
        print(f"[ERROR] fetch_movie_text failed for movie_id={movie_id}: {e}")
        return ''




def get_movie_tfid_matrix(movie_ids):
    movie_texts = []
    movie_id_list = []

    for mid in movie_ids:
        time.sleep(0.3)
        text = fetch_movie_text(mid)
        if text:
            movie_texts.append(text)
            movie_id_list.append(mid)
        if not text:
            print(f"[WARNING] Movie {mid} has no text and was skipped.")
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=3000)
    tfidf_matrix = vectorizer.fit_transform(movie_texts)
    print(vectorizer.get_feature_names_out())

    return movie_id_list, tfidf_matrix



def recommend_similar_movies(movie_id, movie_id_list, cosine_sim ,top_n=10):
    try:
        print(f"[DEBUG] Recommending similar movies for: {movie_id}")
        idx = movie_id_list.index(movie_id)
    except ValueError:
        return []
    
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    print("[DEBUG] Top similarity scores:", sim_scores[:10])
    sim_scores = sim_scores[1:top_n+1]

    recommend_ids = [movie_id_list[i[0]] for i in sim_scores]
    return recommend_ids


def get_top_cast_and_director(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}"
        time.sleep(0.3)
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        top_cast = [c['name'] for c in data['cast'][:1]]
        directors = [d['name'] for d in data['crew'] if d['job'] == 'Director']

        return top_cast, directors

    except Exception as e:
        print(f"[ERROR] Failed to get cast/director for {movie_id}: {e}")
        return [], []


def get_movies_by_person(person_name):
    try:
        # Step 1: Search person by name
        search_url = f"https://api.themoviedb.org/3/search/person?api_key={API_KEY}&query={person_name}"
        time.sleep(0.3)
        search_resp = session.get(search_url, timeout=5)
        search_resp.raise_for_status()
        results = search_resp.json().get('results', [])
        if not results:
            return []

        person_id = results[0]['id']

        # Step 2: Get their movie credits
        credits_url = f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={API_KEY}"
        time.sleep(0.3)
        credits_resp = session.get(credits_url, timeout=5)
        credits_resp.raise_for_status()
        movies = credits_resp.json().get('cast', [])  # or 'crew' for directors

        return [m['id'] for m in movies if 'id' in m]

    except Exception as e:
        print(f"[ERROR] Failed to get movies for {person_name}: {e}")
        return []
    

def fetch_movies_by_genres(genre_ids, language='en', pages=2):
    genre_param = ','.join(map(str, genre_ids))
    movies = []
    for page in range(1, pages + 1):
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_genres={genre_param}&language={language}&sort_by=popularity.desc&page={page}"
        try:
            time.sleep(0.3)
            response = session.get(url, timeout=5)
            response.raise_for_status()
            page_movies = response.json().get('results', [])
            movies.extend(page_movies)
        except Exception as e:
            print(f"[ERROR] Genre fetch failed: {e}")
    return [m['id'] for m in movies]




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
    cast_list = []
    director_list = []
    person_movie_ids = set()
    cast_director_movies = []
    
    if not last_review:
        print("[ERROR] User has not reviewed any movies yet.")

    if last_review:
        movie_id = last_review.movie_id
        print(f"[DEBUG] Base movie ID from last review: {movie_id}")

        cast_list, director_list = get_top_cast_and_director(movie_id)
        person_movie_ids = set()

        for person in cast_list + director_list:
            person_movie_ids.update(get_movies_by_person(person))

        # Remove base movie itself
        person_movie_ids.discard(movie_id)

        # Fetch movie details
        cast_director_movies = [fetch_movie_details(mid) for mid in person_movie_ids]
        cast_director_movies = [movie for movie in cast_director_movies if movie and movie.get('popularity')]
        # ✅ Sort by popularity (or use vote_average or vote_count if preferred)
        cast_director_movies = sorted(cast_director_movies, key=lambda m: m.get('popularity', 0), reverse=True)
        # ✅ Limit to top 20
        cast_director_movies = cast_director_movies[:10]
        print(f"[DEBUG] Top cast: {cast_list}")
        print(f"[DEBUG] Directors: {director_list}")
        print(f"[DEBUG] Found {len(person_movie_ids)} movies by persons")

        genre_map = fetch_genres()

        for movie in cast_director_movies:
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




        # ✅ Fetch base movie genres
        base_movie_data = fetch_movie_details(movie_id)
        base_genres = base_movie_data.get('genres', [])
        genre_ids = [g['id'] for g in base_genres]

        # ✅ Get movies by genre
        genre_based_ids = fetch_movies_by_genres(genre_ids, language='en', pages=2)

        # ✅ Combine person-based + genre-based movies
        all_ids = list(set(genre_based_ids + list(person_movie_ids)))
        if movie_id not in all_ids:
            all_ids.append(movie_id)
        try:
            movie_id_list, tfidf_matrix = get_movie_tfid_matrix(all_ids)
            print(f"[DEBUG] Total movies for TF-IDF: {all_ids}")
            print(f"[DEBUG] Final TF-IDF Movie List: {movie_id_list}")
            print(f"[DEBUG] TF-IDF Matrix Shape: {tfidf_matrix.shape}")
            if movie_id not in movie_id_list:
                print(f"[ERROR] Base movie ID {movie_id} NOT in TF-IDF list")
            else:
                print(f"[DEBUG] Base movie ID {movie_id} FOUND in TF-IDF list")

            cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
            print(f"[DEBUG] Cosine similarity shape: {cosine_sim.shape}")

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
        'person_based_movies': cast_director_movies,
        'base_movie_id': movie_id,
    })



def fetch_movies_by_genre(genre_id,language_code):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_original_language={language_code}&with_genres={genre_id}&sort_by=popularity.desc&page=3"
    try:
        time.sleep(0.3)
        response = session.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get('results', [])
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch movies for genre {genre_id}: {e}")
        return []


#Movies by genre filtering
def movies_by_genre(request, genre_name):
    languages=['en', 'ml', 'ta', 'te', 'hi', 'ka', 'es']
    genre_map = fetch_genres()
    # Reverse genre map: {'Action': 28, ...}
    reverse_genre_map = {v.lower(): k for k, v in genre_map.items()}
    genre_id = reverse_genre_map.get(genre_name.lower())

    if genre_id is None:
        messages.error(request,'Genre not found.')
        return render(request,'user_home_page.html')
    unique_movies = []
    seen_titles = set()

    
    for lang_code in languages:
        movies = fetch_movies_by_genre(genre_id,lang_code)
        
        for movie in movies:
            if movie['title'] not in seen_titles:
                seen_titles.add(movie['title'])
                movie['director'] = get_movie_credits(movie['id'])
                movie['genres'] = [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
                movie['trailer_key'] = get_movie_trailer_key(movie['id'])
                movie['json'] = json.dumps({
                    **movie,
                    "director": movie['director'],
                    "genres": movie['genres'],
                    "trailer_key": movie['trailer_key'],
                })
                unique_movies.append(movie)

    return render(request, 'user_home_page.html', {
        'movies': unique_movies,
        'active_genre': genre_name.title()
    })


#Filtering by language
def movies_by_language(request, lang_code):
    seen_titles = set()
    unique_movies = []
    genre_map = fetch_genres()
    movies = fetch_top_rated_movies(lang_code)

    for movie in movies:
        if movie['title'] not in seen_titles:
            seen_titles.add(movie['title'])
            movie['director'] = get_movie_credits(movie['id'])
            movie['genres'] = [genre_map.get(gid, "Unknown") for gid in movie.get('genre_ids', [])]
            movie['trailer_key'] = get_movie_trailer_key(movie['id'])
            movie['json'] = json.dumps({
                **movie,
                "director": movie['director'],
                "genres": movie['genres'],
                "trailer_key": movie['trailer_key'],
            })
            unique_movies.append(movie)

    return render(request, 'user_home_page.html', {
        'movies': unique_movies,
        'active_language': lang_code
    })