# coding: utf-8
from datetime import datetime
import dateutil.parser
from flask import Flask, abort, json, jsonify, make_response, render_template, Response, request, send_from_directory
import hashlib


# Default configuration
DEBUG = False


# Define greetings for different times of the day in different languages.
GREETINGS = { 
    'english':      ('Good morning', 'Hello', 'Good evening'), 
    'french':       ('Bonjour', 'Bonjour', 'Bonsoir'), 
    'german':       ('Guten morgen', 'Hallo', 'Guten abend'), 
    'spanish':      ('Buenos días', 'Hola', 'Buenas noches'), 
    'portuguese':   ('Bom dia', 'Olá', 'Boa noite'), 
    'italian':      ('Buongiorno', 'Ciao', 'Buonasera'), 
    'swedish':      ('God morgon', 'Hallå', 'God kväll'),
}


app = Flask(__name__, static_url_path='')
app.config.from_object(__name__)
# If there's a HELLOWORLD_SETTINGS environment variable, which should be a
# config filename, use those settings:
app.config.from_envvar('HELLOWORLD_SETTINGS', silent=True)


@app.route('/')
def root():
    return make_response('A Little Printer publication.')

@app.route('/meta.json')
@app.route('/icon.png')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


# == POST parameters:
# :config
#   params[:config] contains a JSON array of responses to the options defined
#   by the fields object in meta.json. In this case, something like:
#   params[:config] = ["name":"SomeName", "lang":"SomeLanguage"]
#
# == Returns:
# A JSON response object.
# If the parameters passed in are valid: {"valid":true}
# If the parameters passed in are not valid: {"valid":false,"errors":["No name was provided"], ["The language you chose does not exist"]}
#
@app.route('/validate_config/', methods=['POST'])
def validate_config():
    if 'config' not in request.form:
        return Response(response='There is no config to validate', status=400)
    
    # Preparing what will be returned:
    response = {
        'errors': [],
        'valid': True,
    }

    # Extract the config from the POST data and parse its JSON contents.
    # user_settings will be something like: {"name":"Alice", "lang":"english"}.
    user_settings = json.loads(request.form.get('config', {}))

    # If the user did not choose a language:
    if 'lang' not in user_settings or user_settings['lang'] == '':
        response['valid'] = False
        response['errors'].append('Please choose a language from the menu.')

    # If the user did not fill in the name option:
    if 'name' not in user_settings or user_settings['name'] == '':
        response['valid'] = False
        response['errors'].append('Please enter your name into the name box.')

    if user_settings['lang'].lower() not in app.config['GREETINGS']:
        # Given that the select field is populated from a list of languages
        # we defined this should never happen. Just in case.
        response['valid'] = False
        response['errors'].append("We couldn't find the language you selected (%s). Please choose another." % user_settings['lang'])

    return jsonify(**response)


# Called to generate the sample shown on BERG Cloud Remote.
#
# == Parameters:
#   None.
#
# == Returns:
# HTML/CSS edition.
#
@app.route('/sample/')
def sample():
    # The values we'll use for the sample:
    language = 'english'
    name = 'Little Printer'
    response = make_response(render_template(
            'edition.html',
            greeting="%s, %s" % (app.config['GREETINGS'][language][0], name),
        ))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    # Set the ETag to match the content.
    response.headers['ETag'] = '"%s"' % (
        hashlib.md5(
            language + name + datetime.utcnow().strftime('%d%m%Y')
        ).hexdigest()
    )
    return response


# Prepares and returns an edition of the publication.
#
# == Parameters:
# lang
#   The language for the greeting.
#   The subscriber will have picked this from the values defined in meta.json.
# name
#   The name of the person to greet.
#   The subscriber will have entered their name at the subscribe stage.
# local_delivery_time
#   The local time where the subscribed bot is.
#
# == Returns:
# HTML/CSS edition with ETag.
# 
@app.route('/edition/')
def edition():
    # Extract configuration provided by user through BERG Cloud.
    # These options are defined in meta.json.
    language = request.args.get('lang', '')
    name = request.args.get('name', '')

    if language == '' or language not in app.config['GREETINGS']:
        return Response(
            response='Error: Invalid or missing lang parameter', status=400)
    
    if name == '':
        return Response(response='Error: No name provided', status=400)

    try:
        # local_delivery_time is like '2013-11-18T23:20:30-08:00'.
        date = dateutil.parser.parse(request.args['local_delivery_time'])
    except:
        return Response(
                    response='Error: Invalid or missing local_delivery_time',
                    status=400)

    # The publication is only delivered on Mondays, so if it's not a Monday in
    # the subscriber's timezone, we return nothing but a 204 status.
    if date.weekday() != 0:
        return Response(response=None, status=204)

    # Pick a time of day appropriate greeting.
    i = 1
    if date.hour >= 0 and date.hour <= 3:
        i = 2
    if date.hour >= 4 and date.hour <= 11:
        i = 0
    elif date.hour >= 12 and date.hour <= 17:
        i = 1
    elif date.hour >= 18 and date.hour <= 23:
        i = 2

    # Base the ETag on the unique content: language, name and time/date.
    # This means the user will not get the same content twice.
    # But, if they reset their subscription (with, say, a different language)
    # they will get new content.
    response = make_response(render_template(
                'edition.html',
                greeting="%s, %s" % (app.config['GREETINGS'][language][i], name)
            ))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['ETag'] = '"%s"' % (
            hashlib.md5(
                language + name + date.strftime('%H%d%m%Y')
            ).hexdigest()
        )
    return response


if __name__ == '__main__':
    app.debug = app.config['DEBUG']
    app.run()

