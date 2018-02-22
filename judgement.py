# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, request, url_for, escape, session
from flask_oauth import OAuth
import model
from credentials import Credentials
import json
GOOGLE_CLIENT_ID = Credentials.google_id 
GOOGLE_CLIENT_SECRET = Credentials.google_secret 
REDIRECT_URI = '/oauth2callback'  # one of the Redirect URIs from Google APIs console

SECRET_KEY = Credentials.secret_key
DEBUG = True 

app = Flask(__name__)

app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth()

google = oauth.remote_app('google',
                          base_url='https://www.google.com/accounts/',
                          authorize_url='https://accounts.google.com/o/oauth2/auth',
                          request_token_url=None,
                          request_token_params={'scope': 'https://www.googleapis.com/auth/userinfo.email',
                                                'response_type': 'code'},
                          access_token_url='https://accounts.google.com/o/oauth2/token',
                          access_token_method='POST',
                          access_token_params={'grant_type': 'authorization_code'},
                          consumer_key=GOOGLE_CLIENT_ID,
                          consumer_secret=GOOGLE_CLIENT_SECRET)

@app.route("/")
def index():
	user_id = session.get("email", None)
	#user_list = model.session.query(model.User).limit(5).all()
	#return render_template("user_list.html", users=user_list, user_id=user_id)
	return render_template("user_list.html", user_id=user_id)

# login as a user 	
@app.route("/login")
def login():
    callback=url_for('authorized', _external=True)
    return google.authorize(callback=callback)

@app.route("/logout")
def logout():
    # remove the username from the session if it's there
    session.pop('id', None)
    session.pop('email', None)
    session.pop('access_token', None)
    return redirect(url_for('index'))

@app.route(REDIRECT_URI)
@google.authorized_handler
def authorized(resp):
    access_token = resp['access_token']
    
    ####################
    #access_token = session.get('access_token')
    #if access_token is None:
    #    return redirect(url_for('login'))
 
    #access_token = access_token[0]
    from urllib2 import Request, urlopen, URLError
 
    headers = {'Authorization': 'OAuth '+access_token}
    req = Request('https://www.googleapis.com/oauth2/v1/userinfo',
                  None, headers)
    res = ''
    try:
        res = urlopen(req)
    except URLError, e:
        if e.code == 401:
            # Unauthorized - bad token
            session.pop('access_token', None)
            return redirect(url_for('login'))
        
    data = json.loads(res.read())
        #return res.read()
 
    #return res.read()
    #############
    session['access_token'] = access_token
    #session['name'] = data["name"].decode("windows-1252").encode("utf8")
    session['email'] = data["email"]
    session['id'] = data["id"]
    return redirect(url_for('index'))
 
@google.tokengetter
def get_access_token():
    return session.get('access_token')

#click on a user and view list of movies they've rated and their ratings
@app.route("/user_ratings_list/<int:id>", methods=["GET"])
def user_ratings_list(id):
	u_ratings_list = model.session.query(model.Rating).filter_by(user_id=id).all()
	return render_template("user_ratings_list.html", u_ratings_list = u_ratings_list)


@app.route("/user_movie_rating/<int:movie_id>/<int:user_id>", methods=["GET"])
def user_movie_rating(movie_id, user_id):
	ind_rating = model.session.query(model.Rating).filter_by(user_id = user_id, movie_id = movie_id).first()
	return render_template("user_movie_rating.html", ind_rating = ind_rating)


@app.route("/rate_movie", methods=["POST"])
def rate_movie():
	
    #get user id
	user_id = request.form['user_id']
	#get movie id
	movie_id = request.form['movie_id']
	#get rating
	rating = request.form['rating']

	#create query
	rating = model.Rating(user_id = user_id, movie_id = movie_id, rating = rating)
	#add the object to a session
	model.session.add(rating)
    #commit session
	model.session.commit()
	return redirect("/")


# view record for a movie and add or update a personal rating for that movie
@app.route("/movie_list")
def movie_list():
	movie_list_query = model.session.query(model.Movie).all()
	user_id = session.get("email", None)
	return render_template("movie_list.html", movie_list = movie_list_query, user_id=user_id)


@app.route("/movie/<int:id>/", methods=["GET"])
def movie(id):
	user_id = session.get("user_id", None)

	user_rating_query = model.session.query(model.Rating).filter_by(user_id=user_id,movie_id=id)
	try:
		user_rating_query.one()
		rating_status = True
		user = user_rating_query.one()
		
	except:
		rating_status = False
		

	movie = model.session.query(model.Rating).filter_by(movie_id=id).all()
	# after getting the session variable back, you have to point it to a page
	return render_template("movie.html", movie = movie, user_id=user_id, rating_status=rating_status)


@app.route("/view_movie/<int:id>/", methods=["GET"])
def view_movie(id):
	movie = model.session.query(model.Movie).get(id)
	ratings = movie.ratings
	rating_nums = []
	user_rating = None
	for r in ratings:
		if r.user_id == session['user_id']:
			user_rating = r
		rating_nums.append(r.rating)
	ave_rating = float(sum(rating_nums))/len(rating_nums)

	#Prediction code (if user hasn't rated)
	user = model.session.query(model.User).get(session['user_id'])
	prediction = None
	if not user_rating:
		prediction = user.predict_rating(movie)
		effective_rating = prediction
	else: 
		effective_rating = user_rating.rating

	the_eye = model.session.query(model.User).filter_by(email="theeye@ofjudgement.com").one()
	eye_rating = model.session.query(model.Rating).filter_by(user_id=the_eye.id, movie_id=movie.id).first()

	if not eye_rating:
		eye_rating = the_eye.predict_rating(movie)
	else:
		eye_rating = eye_rating.rating
	#difference = abs(eye_rating - effective_rating)

	#messages = [ "I suppose you odn't have such bad taste after all.","I regret every decision that I've...","Words fail me, as your taste in movies has clearly failed you.","That movie is great. For a clown to watch. Idiot."]
	
	#beratement = messages[1]
	#end prediction

	return render_template("view_movie.html", movie=movie, average=ave_rating, user_rating=user_rating, prediction=prediction)


# set the secret key.  keep this really secret:
app.secret_key = Credentials.secret_token

if __name__ == "__main__":
	app.run(debug = True)

