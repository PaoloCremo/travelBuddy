from flask import Flask, render_template, request, jsonify

# import gradio as gr
from together import Together
from geopy.geocoders import Nominatim
import googlemaps
import folium
from datetime import datetime
import requests

from dotenv import load_dotenv
import os

load_dotenv()

google_map_api_key = os.getenv("GOOGLE_MAP_API_KEY")

# Get Client
your_api_key = os.getenv("LLM_API_KEY")
client = Together(api_key=your_api_key)

app = Flask(__name__)

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
        
        itinerary = generate_ai_itinerary(city, interests, duration, pace)
        
        return render_template('itinerary.html', 
                               itinerary=itinerary, 
                               city=city, 
                               duration=duration,
                               interests=interests,
                               pace=pace)
    return render_template('create_itinerary.html')

def generate_ai_itinerary(city, interests, duration, pace):
    '''
    main AI place
    call all AI agents and write a complete response
    Agents:
    0. get city weather
    1. generate_first_draft
    2. get_stops
    3. validate_stops
    4. create_itinerary_map
    5. format_itinerary
    '''
    # map_url, first_draft, stops = generate_google_map_url(city, interests, duration, pace)
    weather = get_city_weather(city)
    map_url, first_draft, stops = create_itinerary_map(city, interests, duration, pace, weather)
    final_draft = format_itinerary(first_draft, stops, city, interests, duration, pace, weather)

    itinerary = f"""
    <div class="itinerary-container">
    
    <!-- Left column for text content -->
    <div class="itinerary-text">
    {final_draft}
    </div>
    <div class="map-container">

    <!-- Right column for map -->
    </br>
    <iframe src="{map_url}" width="600" height="450" style="border:0;" allowfullscreen="" loading="lazy"></iframe>
    </div>
    </div>
    """

    return itinerary

def get_city_weather(city):
    """
    Get the weather of a city.
    """

    lat, long = get_lat_long_from_address(city)
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

    # 4. Append the response and image to the chat history
    # chat_history.append((user_message, response))
    return response

def get_stops(city, interests, duration, pace, weather):
    first_drat = generate_first_draft(city, interests, duration, pace, weather)

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
    {first_drat}
    """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        messages=[{"role": "user", "content": chatbot_prompt}],
    )
    response = response.choices[0].message.content

    # 4. Append the response and image to the chat history
    # chat_history.append((user_message, response))
    return response, first_drat

def validate_stops(city, interests, duration, pace, weather):
    stops, first_draft = get_stops(city, interests, duration, pace, weather)

    chatbot_prompt = f"""
    Get the stops from here: {stops} and validate them following the instructions below:
    ## Instructions:
    1. Check if the stops are real places. Not things to do, e.g. "lunch break" is NOT ok
    2. Check if there are no duplicates in the list of stops
    3. Check if the stops are in the right city
    4. Check if the order of the stops make sense. Don't go back and forth in the city. Each stop should be next to the previous one.
    6. give a semicolon separated list of stops. Each stop has: stop, city, country
    E.g.: Griffith Observatory, Los Angeles, USA; Beverly Hills, Los Angeles, USA

    Important! Write your response in the following format:
    'Exaplanation: explanation.
    List of Stops: stop1, city, country; stop2, city, country; etc.'
    """

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        messages=[{"role": "user", "content": chatbot_prompt}],
    )
    response = response.choices[0].message.content

    return response, first_draft

def create_itinerary_map(city, interests, duration, pace, weather, mode="walking"):
    """
    Create an embedded map with an itinerary from a list of stops.
    
    Args:
        api_key (str): Google Maps API key
        stops (list): List of stop names or addresses
        mode (str): Travel mode (driving, walking, bicycling, transit)
    
    Returns:
        folium.Map: Map object that can be saved as HTML
    """
    # Initialize Google Maps client
    stops_verb, first_draft = validate_stops(city, interests, duration, pace, weather)
    stop_list = stops_verb.split(':')[-1].split(';')
    stops = [stop.replace("\n", "").replace('&', 'and').strip().replace(' ', '+') for stop in stop_list]
    way_points = '|'.join(stops[1:-1])

    base_url = 'https://www.google.com/maps/embed/v1/directions'
    api_key = google_map_api_key
    '&origin=San+Francisco&destination=Los+Angeles&waypoints=In-N-Out+Burger,+San+Jose|Fresno&mode=driving'

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

def get_lat_long_from_address(address):
   locator = Nominatim(user_agent='myGeocoder')
   location = locator.geocode(address)
   return location.latitude, location.longitude

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

if __name__ == '__main__':
    app.run(debug=False)
