import json
import dateutil.parser
from datetime import datetime
import babel
from flask import render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import *
from config import db, app

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    areas = Venue.query.with_entities(
        Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()
    upcoming_shows = Show.query.with_entities(Show.venue_id, db.func.count(
        "*").label("num_upcoming_shows")).filter(Show.start_time > datetime.today()).group_by(Show.venue_id).subquery()

    data = []
    for area in areas:
        data.append({
            "city": area.city,
            "state": area.state,
            "venues": Venue.query.filter(Venue.city == area.city).with_entities(Venue.id, Venue.name, upcoming_shows.c.num_upcoming_shows).outerjoin(upcoming_shows, upcoming_shows.c.venue_id == Venue.id).all()
        })

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():

    search_term = '%{}%'.format(request.form.get('search_term', ''))
    venues = Venue.query.filter(Venue.name.ilike(search_term)).all()

    response = {'count': len(venues), 'data': venues}

    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  venue = Venue.query.get(venue_id)

  past_shows = list(filter(lambda x: x.start_time < datetime.today(), venue.shows))
  upcoming_shows = list(filter(lambda x: x.start_time >= datetime.today(), venue.shows))

  past_shows = list(map(lambda x: x.show_artist(), past_shows))
  upcoming_shows = list(map(lambda x: x.show_artist(), upcoming_shows))

  data = venue.venue_to_dictionary()

  data['past_shows'] = past_shows
  data['past_shows_count'] = len(past_shows)

  data['upcoming_shows'] = upcoming_shows
  data['upcoming_shows_count'] = len(upcoming_shows)

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

    try:
        form = {**request.form}
        form['genres'] = ','.join(request.form.getlist("genres"))
        venue = Venue(**form)
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed.')
        abort(400)

    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):

    venue = Venue.query.get(venue_id)
    try:
        db.session.delete(venue)
        db.session.commit()
        flash('Venue ' + venue.name + ' was successfully deleted!')

    except:
        db.session.rollback()
        flash('An error occurred. Venue ' +
              venue.name + ' could not be deleted.')
        abort(400)

    finally:
        db.session.close()

    return None


@app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):

    artist = Artist.query.get(artist_id)
    try:
        db.session.delete(artist)
        db.session.commit()
        flash('Artist ' + artist.name + ' was successfully deleted!')

    except:
        db.session.rollback()
        flash('An error occurred. Artist ' +
              artist.name + ' could not be deleted.')
        abort(400)

    finally:
        db.session.close()

    return None

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():

    artists = Artist.query.with_entities(Artist.id, Artist.name).all()

    return render_template('pages/artists.html', artists=artists)


@app.route('/artists/search', methods=['POST'])
def search_artists():

    artists = Artist.query.with_entities(Artist.id, Artist.name).filter(Artist.name.ilike(
        f"%{request.form.get('search_term', '')}%")).all()

    response = {'count': len(artists), 'data': artists}

    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

    artist = Artist.query.get(artist_id)
    upcoming_shows = Show.query.join(Show.venue).with_entities(Venue.id.label("venue_id"), Venue.name.label("venue_name"), Venue.image_link.label("venue_image_link"), Show.start_time).filter(
        Show.artist_id == artist_id, Show.start_time > datetime.today()).all()
    past_shows = Show.query.join(Show.venue).with_entities(Venue.id.label("venue_id"), Venue.name.label("venue_name"), Venue.image_link.label("venue_image_link"), Show.start_time).filter(
        Show.artist_id == artist_id, Show.start_time <= datetime.today()).all()

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres.split(","),
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "image_link": artist.image_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,

        "upcoming_shows": upcoming_shows,
        "past_shows": past_shows,
        "upcoming_shows_count": len(upcoming_shows),
        "past_shows_count": len(past_shows)
    }

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@ app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    form = ArtistForm(obj=artist)
    form.genres.data = artist.genres.split(",")
    
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@ app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):

    try:
        form = {**request.form}
        form['genres'] = ','.join(request.form.getlist("genres"))
        artist = Artist.query.get(artist_id)
        for key, value in form.items():
            setattr(artist, key, value)

        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully updated!')

    except:
        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be updated.')
        abort(400)

    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@ app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    form = VenueForm(obj=venue, genres=venue.genres.split(","))
    form.genres.data = venue.genres.split(",")

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@ app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

    try:
        form = {**request.form}
        form['genres'] = ','.join(request.form.getlist("genres"))
        venue = Venue.query.get(venue_id)
        for key, value in form.items():
            setattr(venue, key, value)

        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully updated!')

    except:
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be updated.')
        abort(400)

    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@ app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@ app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    try:
        form = {**request.form}
        form['genres'] = ','.join(request.form.getlist("genres"))
        artist = Artist(**form)
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')

    except:
        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed.')
        abort(400)

    finally:
        db.session.close()

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@ app.route('/shows')
def shows():
    shows = Show.query.join(Venue).join(Artist).with_entities(Show.venue_id, Show.artist_id, Show.start_time,
                                                              Venue.name.label("venue_name"), Artist.name.label("artist_name"), Artist.image_link.label("artist_image_link")).all()
    return render_template('pages/shows.html', shows=shows)


@ app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@ app.route('/shows/create', methods=['POST'])
def create_show_submission():
    try:
        show = Show(**request.form)
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Show could not be listed.')
        abort(400)

    finally:
        db.session.close()

    return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    if type(value) is str:
        date = dateutil.parser.parse(value)
    else:
        date = value

    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
