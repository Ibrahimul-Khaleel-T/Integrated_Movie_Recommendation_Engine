from django.shortcuts import render,redirect
from django.http import HttpResponse
from .models import UserInfo
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
from django.core.mail import send_mail
import random,requests,json
API_KEY="830596140937bda925ac2c89f6deb604"

# Create your views here.

def index(request):
    return render(request,'index_page.html')


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



def dp(request):
    user = request.user
    if request.method == 'POST':
        dp = request.FILES.get('dp')
        if dp:
            user.dp = dp
        elif not user.dp:
            user.dp = 'default_images/default_dp2.jpeg'
        user.save()
        return redirect(user_home_page)
    return render(request,'dp.html',{'user':user})


def signup(request):
    if request.method=='POST':
        fullname=request.POST['fullname']
        email=request.POST['email']
        mobile_number=request.POST['mobile_number']
        username=request.POST['username']
        password=request.POST['password']
        if UserInfo.objects.filter(username=username).exists():
            messages.error(request,"The Username is not available,Try another one.")
            return render(request,'signup_page.html')
        
        data=UserInfo.objects.create_user(fullname=fullname,email=email,mobile_number=mobile_number,username=username,password=password)
        data.save()
        user=authenticate(username=username,password=password)
        login(request,user)
        return redirect(dp)
    else:
        return render(request,'signup_page.html')


def signin(request):
    if request.method=='POST':
        username=request.POST['username']
        password=request.POST['password']
        user=authenticate(username=username,password=password)
        if user is not None:
            login(request,user)
            return redirect(user_home_page)
        else:
            messages.error(request,"Invalid Username or Password, Try again!")
            return render(request,'signin_page.html')
    else:
        return render(request,'signin_page.html')
 
    
def send_otp(email):
    otp = random.randint(100000,999999)
    send_mail(
        'Your OTP Code',''
        f'Your OTP code is: {otp}',
        'kha7ee7@gmail.com',
        [email],
        fail_silently=False,
    )
    return otp


def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST['email']
        print(email)
        try:
            user = UserInfo.objects.get(email=email)
            otp = send_otp(email)
            print(otp)

            context = {
                        "email": email,
                        "otp": otp,
            }
            return render(request,'verify_otp.html',context)
        
        except UserInfo.DoesNotExist:
            messages.error(request,'Email address not found.')
    else:
        return render(request,'reset_password.html')
    return render(request,'reset_password.html') 


def verify_otp(request):
    if request.method == 'POST':
        email =request.POST.get('email')
        otpold = request.POST.get('otpold')
        otp = request.POST.get('otp')

        if otpold==otp :
            context = {
                'otp' : otp,
                'email': email
            }
            return render(request,'set_new_password.html',context)
        else:
            messages.error(request,"Invalid OTP")
        return render(request,'verify_otp.html',{'email':email})
    return render(request,'verify_otp.html') 


def set_new_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'set_new_password.html', {'email': email})
        try:
            data = UserInfo.objects.get(email=email)
            data.set_password(new_password)
            data.save()
            messages.success(request,'Password has been reset successfully')
            return redirect(signin)
        except UserInfo.DoesNotExist:
            messages.error(request,'User not found!')
            return render(request,'set_new_password.html',{'email':email})  
    email = request.GET.get('email', '')             
    return render(request,'set_new_password.html',{'email':email})


def signout(request):
    logout(request)
    return redirect(signin)


def user_profile(request):
    try:
        data=request.user
        return render(request,'user_profile.html',{'data':data})
    except UserInfo.DoesNotExist:
        return redirect(user_home_page)
    except:
        return redirect(user_home_page)
    

def edit_user_profile(request):
    data=request.user
    if request.method=='POST':
        if 'dp' in request.FILES:
            data.dp=request.FILES['dp']
        data.username=request.POST['username']
        data.fullname=request.POST['fullname']
        data.email=request.POST['email']
        data.mobile_number=request.POST['mobile_number']
        data.save()
        messages.success(request,"The changes are successfully updated.")
        return redirect(user_profile)
    else:
        return render(request,'edit_user_profile.html',{'data':data})




