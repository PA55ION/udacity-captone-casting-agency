import os
from flask import Flask, session, url_for, flash
from flask import abort
from flask import jsonify
from flask import request
from flask import render_template
from flask import redirect
import json
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from models import setup_db, Movies, Actors, rollback
from auth import AuthError, requires_auth
from flask_wtf import FlaskForm
from forms import *
import sys


SECRET_KEY = os.urandom(32)
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
AUTH0_API_AUDIENCE = os.environ.get('AUTH0_API_AUDIENCE')
AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL')
AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
AUTH0_BASE_URL = 'https://{AUTH0_DOMAIN}'


def create_app(test_config=None):
    # create and configure the app

    app = Flask(__name__)
    db = setup_db(app)
    app.config['SECRET_KEY'] = SECRET_KEY
    cors = CORS(app, resources={r'/api/*': {'origins': '*'}})
    oauth = OAuth(app)

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET, PATCH,  POST, DELETE, OPTIONS')
        return response

    auth0 = oauth.register(
        'auth0',
        client_id='Er4ULFDP3EJpPh3Ds6Pu1kgNGN6yI2mz',
        client_secret='YOUR_CLIENT_SECRET',
        api_base_url='https://dev-ys0-cxsi.us.auth0.com',
        access_token_url='https://dev-ys0-cxsi.us.auth0.com/oauth/token',
        authorize_url='https://dev-ys0-cxsi.us.auth0.com/authorize',
        # client_id=AUTH0_CLIENT_ID,
        # client_secret=AUTH0_CLIENT_SECRET,
        # api_base_url=AUTH0_BASE_URL,
        # access_token_url=AUTH0_BASE_URL + '/oauth/token',
        # authorize_url=AUTH0_BASE_URL + '/authorize',
    )

    @app.route('/')
    def index():
        return render_template('layouts/home.html')

    @app.route('/logout')
    def logout():
        session.clear()
        # return ('Logout', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})
        params = {'returnTo': url_for(
            'home', _external=True), 'client_id': 'Er4ULFDP3EJpPh3Ds6Pu1kgNGN6yI2mz'}
        return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

    # @app.route('/login')
    # def login():
    #   return auth0.authorize_redirect(redirect_uri='http://127.0.0.1:5000/')

    @app.route('/callback')
    def callback_handling():
        auth0.authorize_access_token()
        resp = auth0.get('userinfo')
        userinfo = resp.json()

        session['jwt.payload'] = userinfo
        session['profile'] = {
            'user_id': userinfo['sub'],
            'name': userinfo['name'],
            'picture': userinfo['picture']
        }

        return redirect('/layouts/home.html')

    @app.route('/movies')
    def get_movies():
        movies = Movies.query.all()
        # try:
        #   movies = Movies.query.all()
        #   all_movies = [movie.format() for movie in movies]
        #   print(all_movies)
        #   return jsonify({
        #     'success': True,
        #     'movies': all_movies,
        #   })
        # except Exception as e:
        #   print(e)

        return render_template('pages/movies.html', movies=movies)

    @app.route('/add_movie', methods=['GET'])
    def create_movie_form():
        # form = MovieForm()
        return render_template('forms/new_movies.html')

    @app.route('/movies/<int:movie_id>')
    def edit_movie(movie_id):
        form = MovieForm()
        movie = Movies.query.get(movie_id)
        form.title.data = movie.title
        form.release_date.data = movie.release_date
        form.description.data = movie.description
        form.image_link.data = movie.image_link
        return render_template('forms/edit_movie.html', form=form, movie=movie)

    # TODO add auth token for director and executive producer
    @app.route('/movies/<int:movie_id>', methods=['DELETE'])
    # @requires_auth('delete:actors')
    def delete_movie(movie_id):
        try:
            movie = Movies.query.get(movie_id)
            name = movie.title
            movie.delete()
            return jsonify({
                'success': True,
                'deleted': movie.id,
                'message': 'Movie ' + name + ' successfully deleted'
            }), 200
        except Exception:
            return json.dumps({
                'success': False,
                'error': 'Movie not found'
            }), 404
# TODO add auth token for director and executive producer

    @app.route('/add_movies', methods=['POST'])
    # @requires_auth('post:movies')
    def add_movie():
        # def post_movie(token):
        # data = request.get_json()
        error = False
        new_title = request.form['title']
        new_release_date = request.form['release_date']
        new_image_link = request.form['image_link']
        new_description = request.form['description']

        try:
            movie = Movies(title=new_title, release_date=new_release_date,
                           description=new_description, image_link=new_image_link)
            movie.insert()

            selection = Movies.query.order_by('id').all()
            flash(movie.title + 'successfully added')
            return jsonify({
                'success': True,
                'message': 'Movie ' + movie.title + ' successfully added',
                'movies': len(selection)
            })

        except Exception:
            return json.dumps({
                'success': False,
                'error': 'Not able to add movie at this time',
            }), 422

# TODO add auth token for director and executive producer
    @app.route('/movies/<int:movie_id>', methods=['PATCH', 'POST'])
    # @requires_auth('patch:movies')
    def update_movie(movie_id):
       # @requires_auth('patch:actors')
        # def update_actor(token, actor_id):
        error = False
        # actor = Actors.query.filter(Actors.id == actor_id).one_or_none()
        movie= Movies.query.get(movie_id)

        try:
            movie.title = request.form['title']
            movie.description = request.form['description']
            movie.release_date = request.form['release_date']
            movie.image_link = request.form['image_link']
            movie.update()
            flash(request.form['title'] + ' successfully updated 🚀 ')
        except BaseException:
            rollback()
            flash(request.form['title'] + ' cannot be updated! 😞')
            
        return redirect(url_for('get_movies', movie_id=movie_id))
        # movie = Movies.query.filter(Movies.id == movie_id).one_or_none()
        # if movie:
        #     try:
        #         data = request.get_json()
        #         update_title = data.get('title', None)
        #         update_release_date = data.get('release_date', None)
        #         update_image = data.get('image_link', None)
        #         update_description = data.get('description', None)
        #         if update_title:
        #             movie.title = update_title
        #         if update_release_date:
        #             movie.release_date = update_release_date
        #         if update_image:
        #             movie.image_link = update_image
        #         if update_description:
        #             movie.description = update_description
        #         movie.update()
        #         return jsonify({
        #             'success': True,
        #             'movies': movie.format()
        #         })
        #     except Exception:
        #         return json.dumps({
        #             'success': False,
        #             'error': 'Bad request'
        #         }), 400

# COMMENT endpoints for actors
    @app.route('/actors')
    def get_actors():
        actors = Actors.query.all()
        # try:
        #   actors = Actors.query.all()
        #   actor_list = [actor.format() for actor in actors]
        #   print(actor_list)
        #   return jsonify({
        #     'success': True,
        #     'actors': actor_list
        #   }), 200

        # except Exception:
        #   return json.dumps({
        #     'success': False,
        #     'error': 'Actor not found.'
        #   }), 404

        return render_template('pages/actors.html', actors=actors)
    # TODO add auth token for director and executive producer

    @app.route('/add_actor', methods=['POST'])
    def add_actor():
        # @requires_auth('post:actors')
        # def post_actor(token):
        error = False
        new_name = request.form['name']
        new_age = request.form['age']
        new_gender = request.form['gender']
        new_image_link = request.form['image_link']

        try:
            actor = Actors(name=new_name, age=new_age,
                           gender=new_gender, image_link=new_image_link)
            actor.insert()
            flash('Artist ' + request.form['name'] + ' successfully created 🚀')

        except Exception:
            rollback()
            error = True
            abort(400)
            flash('An error occurred. ' + actor.name + ' could not be listed.')
       
        return redirect(url_for('get_actors'))

# TODO add auth token for director and executive producer

    @app.route('/actors/<int:actor_id>', methods=['DELETE'])
    def delete_actor(actor_id):
        # @requires_auth('delete:actors')
        # def delete_actor(token, actor_id):
        try:
            actor = Actors.query.get(actor_id)
            name = actor.name
            actor.delete()
            flash('Model ' + name + ' successfully deleted!')
            return jsonify({
                'success': True,
                'message': 'Actor successfully deleted.',
                'actors': actor.id
            }), 200
        except Exception:
            flash('Model ' + name + 'can not be delete at this time. Please try again later')
            return json.dumps({
                'success': False,
                'error': 'Actor not found.'
            }), 404
# TODO add auth token for director and executive producer

    @app.route('/actors/<int:actor_id>', methods=['PATCH', 'POST'])
    def update_actor(actor_id):
        # @requires_auth('patch:actors')
        # def update_actor(token, actor_id):
        error = False
        # actor = Actors.query.filter(Actors.id == actor_id).one_or_none()
        actor = Actors.query.get(actor_id)

        try:
            actor.name = request.form['name']
            actor.age = request.form['age']
            actor.gender = request.form['gender']
            actor.image_link = request.form['image_link']
            actor.update()
            flash(request.form['name'] + ' successfully updated 🚀 ')
        except BaseException:
            rollback()
            flash(request.form['name'] + ' cannot be updated! 😞')
            
        return redirect(url_for('get_actors', actor_id=actor_id))

        # if actor:
        #   try:
        #     data = request.get_json()
        #     update_name = data.get('name', None)
        #     update_age = data.get('age', None)
        #     update_gender = data.get('gender', None)
        #     update_image = data.get('image_link', None)
        #     if update_name:
        #       actor.name = update_name
        #     if update_age:
        #       actor.age = update_age
        #     if update_gender:
        #       actor.gender = update_gender
        #     if update_image:
        #       actor.image_link = update_image

        #     actor.update()

        #     return jsonify({
        #       'success': True,
        #       'message': 'Successfully updated.',
        #       'actors': actor.format()
        #     }), 200
        #   except Exception:
        #     return json.dumps({
        #       'success': False,
        #       'error': 'Bad request.',
        #     }), 400

    @app.route('/add_actor', methods=['GET'])
    def create_actor_form():
        form = ActorForm()
        return render_template('forms/new_actors.html', form=form)

    @app.route('/actors/<int:actor_id>')
    def edit_actor(actor_id):
        form = ActorForm()
        actor = Actors.query.get(actor_id)
        form.name.data = actor.name
        form.age.data = actor.age
        form.gender.data = actor.gender
        form.image_link.data = actor.image_link
        return render_template('forms/edit_actor.html', form=form, actor=actor)

    # COMMENT error handler
    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({
            'success': False,
            'error': 422,
            "message": "Unprocessable"
        }), 422

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 404,
            'message': "Not found"
        }), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'success': False,
            'message': "Internal server error",
            'error': 500
        }), 500

    @app.errorhandler(AuthError)
    def auth_error(ex):
        response = jsonify(ex.error)
        response.status_code = ex.status_code
        return response

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
    # app.run()

