from flask import Flask, render_template, request, jsonify

# import gradio as gr
from together import Together
from geopy.geocoders import Nominatim
import requests

from dotenv import load_dotenv
import os

load_dotenv()

google_map_api_key = os.getenv("GOOGLE_MAP_API_KEY")

# Get Client
your_api_key = os.getenv("LLM_API_KEY")
client = Together(api_key=your_api_key)

app = Flask(__name__)


###############
## TEST DATA ##
###############

final_draft_test =  '''
    <h3>Day 1:</h3>
    <ul>
        <li><strong>6:00 PM:</strong> We'll begin our adventure at Golden Gate Park, one of San Francisco's most iconic natural attractions. This 1,017-acre park is a haven for nature lovers, with its lush greenery, walking trails, and scenic views of the city. We'll take a leisurely stroll through the park, enjoying the evening sun and the sounds of nature.</li>
        <li><strong>6:30 PM:</strong> From Golden Gate Park, we'll head to the Presidio, a former military base turned national park. This 1,500-acre park offers stunning views of the Golden Gate Bridge, the Bay, and the city skyline. We'll take a short walk along the Presidio's scenic trails, enjoying the sunset and the tranquil atmosphere.</li>
        <li><strong>7:15 PM:</strong> Next, we'll head to Fisherman's Wharf, a bustling waterfront district famous for its seafood restaurants, street performers, and stunning views of the Bay Bridge. We'll grab a bite to eat at one of the many eateries, sampling some of the city's famous seafood delicacies.</li>
        <li><strong>8:00 PM:</strong> After dinner, we'll head to Pier 39, a popular spot for seafood, street performers, and live music. We'll take a leisurely stroll along the pier, enjoying the evening atmosphere and the views of the Bay.</li>
        <li><strong>9:00 PM:</strong> Finally, we'll end our evening at the Ferry Building Marketplace, a historic landmark turned food hall. This bustling marketplace offers a variety of artisanal food vendors, restaurants, and bars. We'll sample some of the city's best food and drinks, from artisanal cheeses to craft beers.</li>
    </ul>
    <h4>Useful Tips:</h4>
    <ul>
        <li>The current weather is perfect for an evening stroll, with a comfortable temperature of 23.1°C (73.6°F) and a clear sky.</li>
        <li>Don't forget to pack light clothing for the mild temperature, but be prepared for a light jacket or sweater for the evening.</li>
        <li>Take advantage of the clear sky to capture stunning photos of the city's iconic landmarks, such as the Golden Gate Bridge or the San Francisco Bay.</li>
        <li>Be prepared for crowds at popular tourist spots, and consider visiting during the evening hours to avoid the midday rush.</li>
    </ul>
    '''

list_of_stops_test = '''
Golden Gate Park, San Francisco, USA; The Presidio, San Francisco, USA; Fisherman's Wharf, San Francisco, USA; Pier 39, San Francisco, USA; Ferry Building Marketplace, San Francisco, USA&mode=walking
'''

###################
## END TEST DATA ##
###################

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/create_itinerary', methods=['GET', 'POST'])
def create_itinerary():
    if request.method == 'POST':
        city = request.form.get('city')
        interests = request.form.get('interests')
        duration = int(request.form.get('duration'))
        pace = request.form.get('pace')
        
        itinerary, stops = generate_ai_itinerary(city, interests, duration, pace, 
                                                 tryout=False)
        
        return render_template('itinerary.html', 
                               itinerary=itinerary, 
                               city=city, 
                               duration=duration,
                               interests=interests,
                               pace=pace,
                               stops=stops)
    return render_template('create_itinerary.html')

def generate_ai_itinerary(city, interests, duration, pace, tryout=False):
    '''
    main AI place
    call all AI agents and write a complete response
    Agents:
    1. get city weather
    2. generate_first_draft
    3. get_stops
    4. validate_stops
    5. format_itinerary

    6. map is created with the webpage
    '''
    if tryout:
        
        final_draft = final_draft_test
        stops = list_of_stops_test

    else:
        # 1. get city weather
        weather = get_city_weather(city)
    
        # 2. generate_first_draft
        first_draft = generate_first_draft(city, interests, duration, pace, weather)
    
        # 3. get_stops
        stops_0 = get_stops(first_draft)
    
        # 4. validate_stops
        stops = validate_stops(stops_0, city)
        stops = stops.replace('&', 'and')
    
        # 5. format itinerary
        final_draft = format_itinerary(first_draft, stops, city, interests, duration, pace, weather)
    

    return final_draft, stops

def get_city_weather(city):
    """
    Get the weather of a city.
    """
    
    try:
        lat, long = get_lat_long_from_address(city)
    except:
        lat, long = get_lat_long_from_google(city)

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&current_weather=true"
    
    resp = requests.get(url)
    if resp.status_code == 200:
        weather = resp.json()
    else:
        raise ValueError("Unable to fetch weather data")
    
    chatbot_prompt = f"""
    Interpret the weather of the city {city} from {weather} and write a summary of it.
    Give suggestions on whether it is a good time to visit the city or not, if it's too hot or too cold to be outside, etc.
    """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        messages=[{"role": "user", "content": chatbot_prompt}],
    )
    response = response.choices[0].message.content

    return response


def generate_first_draft(city, interests, duration, pace, weather):
    
    chatbot_prompt = f"""
    You are a local tour guide in {city} helping tourists to find the best places to visit.
    They have these interests: {interests}.
    They want to visit the city with this pace: {pace}; and in this time: {duration} days. 
    Also, the weather in the city is {weather}.
    So adapt your answers to it.

    ## Instructions:
    * adapt your answer to the city, interests, duration, pace, and weather
    * be as thorough as possible. Don't leave behind any details
    * Give a detailed verbose response
    * add a precise list of stops
    """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        messages=[{"role": "user", "content": chatbot_prompt}],
    )
    response = response.choices[0].message.content

    return response

def get_stops(first_draft):

    chatbot_prompt = f"""
    Get the stops from the first draft and format them following the instructions below:
    ## Instructions:
    ** semicolon separated list of stops. Each stop has: stop, city, country
    E.g.: Griffith Observatory, Los Angeles, USA; Beverly Hills, Los Angeles, USA **
    ** be sure to include all the stops from the first draft **
    ** be sure there are no duplicates in the list of stops **
    ** be sure that each stop is a real place. Not a thing to do, e.g. "lunch break" is NOT ok **
    ** don't add anything else to your response. Just the list of stops **

    Here is the first draft:
    {first_draft}
    """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        messages=[{"role": "user", "content": chatbot_prompt}],
    )
    response = response.choices[0].message.content

    return response

def validate_stops(stops, city):

    chatbot_prompt = f"""
    Get the stops from here: {stops} and validate them following the instructions below:
    ## Instructions:
    0. Check that the stopps are in the right city, i.e. {city}
    1. Check if the stops are real places. Not general things, e.g. "lunch break", but specific ones, e.g. "lunch break at La Terrazza in Vancouver" yes! Museums, parks, restaurants etc. are very ok!
    2. Check if there are no duplicates in the list of stops
    3. Check if the stops are in the right city
    4. Check if the order of the stops make sense. Don't go back and forth in the city. Each stop should be next to the previous one.
    6. give a semicolon separated list of stops. Each stop has: stop, city, country
    E.g.: Griffith Observatory, Los Angeles, USA; Beverly Hills, Los Angeles, USA

    Important! Write your response in the following format:
    'Exaplanation: explanation.
     Other stuff, like stops removed.
     List of Stops: stop1, city, country; stop2, city, country; etc.'
     
    IMPORTANT! Do not add anything else after the list of stops!
    """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        messages=[{"role": "user", "content": chatbot_prompt}],
    )
    response = response.choices[0].message.content

    return response

@app.route('/get_map_url', methods=['GET'])
def get_map_url():

    stops_verb = request.args.get('stops')
    mode = request.args.get('mode', 'walking')

    stop_list = stops_verb.split(':')[-1].split(';')
    stops_fin = [stop.replace("\n", "").replace('&', 'and').strip().replace(' ', '+') for stop in stop_list]
    way_points = '|'.join(stops_fin[1:-1])

    base_url = 'https://www.google.com/maps/embed/v1/directions'
    api_key = google_map_api_key

    my_map = (
    f"{base_url}?key={api_key}"
    f"&origin={stops_fin[0]}"
    f"&destination={stops_fin[-1]}"
    f"&waypoints={way_points}"
    f"&mode={mode}"
    )

    return jsonify({'map_url': my_map})

def format_itinerary(first_draft, stops, city, interests, duration, pace, weather):

    chatbot_prompt = f"""
    You are a local tour guide in {city} helping tourists to find the best places to visit.
    They have these interests: {interests}.
    They want to visit the city with this pace: {pace}; and in this time: {duration}. 
    Read the first draft - {first_draft} - and the list of stops - {stops} - and write a complete response.
    Include information about the weather: {weather}.

    # Instructions:
    - don't include the first draft in your response
    - summarise a bit the explanation from the first draft
    - don't include the raw list of stops in your response
    - add some useful tips for the tourists

    Format your response following the example below. It is important to list the stops in the right order with some explanation:
    '
    <h2>Welcome to {city}!</h2>
    <p>I'd be happy to help you plan your {duration}-day adventure in this amazing city! 
    Given your interests in {interests}, I've curated a {pace}-paced itinerary for you.</p>
    
    <div class="day-container">
        <h3>Day 1:</h3>
        <ul>
            <li><strong>10:00 AM:</strong> Visit the main attractions</li>
            <li><strong>2:00 PM:</strong> Explore local cuisine</li>
            <li><strong>6:00 PM:</strong> Evening entertainment</li>
        </ul>
        <h4>Useful Tips:</h4>
        <ul>
            <li>something about the weather</li>
            <li>Wear comfortable shoes</li>
            <li>Bring a camera</li>
        </ul>
    </div>
    '
    """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        messages=[{"role": "user", "content": chatbot_prompt}],
    )
    final_draft = response.choices[0].message.content

    return final_draft

def get_lat_long_from_address(address):
   locator = Nominatim(user_agent='myGeocoder')
   location = locator.geocode(address)
   return location.latitude, location.longitude

def get_lat_long_from_google(address):
    
    response = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?key={google_map_api_key}&address={address}')

    resp_json_payload = response.json()
    
    out = resp_json_payload['results'][0]['geometry']['location']

    return out['lat'], out['lng']

# other useful functions

def create_itinerary_map(city, interests, duration, pace, weather, mode="walking"):
    """
    Create an embedded map with an itinerary from a list of stops.
    
    Args:
        api_key (str): Google Maps API key
        stops (list): List of stop names or addresses
        mode (str): Travel mode (driving, walking, bicycling, transit)
    
    Returns:
        
    """
    # Initialize Google Maps client
    stops_verb, first_draft = validate_stops(city, interests, duration, pace, weather)
    stop_list = stops_verb.split(':')[-1].split(';')
    stops = [stop.replace("\n", "").replace('&', 'and').strip().replace(' ', '+') for stop in stop_list]
    way_points = '|'.join(stops[1:-1])

    base_url = 'https://www.google.com/maps/embed/v1/directions'
    api_key = google_map_api_key

    my_map = (
    f"{base_url}?key={api_key}"
    f"&origin={stops[0]}"
    f"&destination={stops[-1]}"
    f"&waypoints={way_points}"
    f"&mode={mode}"
    )

    
    return my_map, first_draft, stops

def generate_stops_dict(city, interests, duration, pace):
    stops_verb, first_draft = get_stops(city, interests, duration, pace)
    stop_list = stops_verb.split(':')[-1].split(";")
    stops = []
    for stop in stop_list:
        stop = stop.replace("\n", "").strip()
        try:
            lat, lng = get_lat_long_from_address(stop)
        except AttributeError:
            lat, lng = get_lat_long_from_address(city)
        stop_dict = {
            "name": stop,
            "lat": lat,
            "lng": lng
        }
        stops.append(stop_dict)

    return stops, first_draft

if __name__ == '__main__':
    app.run(debug=False)