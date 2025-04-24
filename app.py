from flask import Flask, render_template, request, jsonify

from together import Together
from geopy.geocoders import Nominatim
import requests
from google import genai

from dotenv import load_dotenv
import os

from datetime import datetime
import asyncio

load_dotenv()

# api keys
google_map_api_key = os.getenv("GOOGLE_MAP_API_KEY")
meta_api_key = os.getenv("TOGETHER_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")

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
        model = request.form.get('llm')
        print(model)
        set_global_llm_model(model, verbose=True)
        
        itinerary, stops = generate_ai_itinerary(city, interests, duration, pace, 
                                                 tryout=False, verbose=True)
        
        return render_template('itinerary.html', 
                               itinerary=itinerary, 
                               city=city, 
                               duration=duration,
                               interests=interests,
                               pace=pace,
                               stops=stops,
                               llm=model)
    return render_template('create_itinerary.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if request.method == 'POST':
        feedback = request.form.get('feedback')
    
        old_itinerary = request.form.get('itinerary')
        city = request.form.get('city')
        interests = request.form.get('interests')
        duration = request.form.get('duration')
        pace = request.form.get('pace')
        model = request.form.get('new_llm')
        old_stops = request.form.get('stops')
    
        print(f"llm_model: {model}")
        
        set_global_llm_model(model, verbose=True)
    
        itinerary, stops = generate_revised_ai_itinerary(feedback, 
                                                         old_itinerary, old_stops,
                                                         city, interests, duration, pace, 
                                                         tryout=False, verbose=True)
        
        print(f"itinerary: {itinerary}\nstops: {stops}")
        
        return render_template('itinerary.html', 
                               itinerary=itinerary, 
                               city=city, 
                               duration=duration,
                               interests=interests,
                               pace=pace,
                               stops=stops,
                               llm=model)
    
    return render_template('create_itinerary.html')

@app.route('/stop/<stop_name>', methods=['GET', 'POST'])
def stop_page(stop_name, tryout=False):
    if tryout:
        from test.test import more_info_test, description_test, stop_name_test
        
        stop_name = stop_name_test
        description = description_test
        ai_response = more_info_test

    else:
        # Get the description from the query parameters
        description = request.args.get('description', 'No description provided.')
        
        # Replace %20 with spaces for readability
        stop_name = stop_name.replace('%20', ' ')
        description = description.replace('%20', ' ')
        
        # Generate a detailed explanation using the AI
        chatbot_prompt = f"""
        Provide a detailed explanation for {stop_name}. Description: {description}
        ## Instructions:
        - be clear 
        - provide some suggestions
        - add some link to more info
        
        Finally, format your response in HTML!
        # Instructions:
        - do not add any other text
        - DO NOT put <body>, <html>, <head>, <table> tags. It will be embedded in a webpage. Do not either start with ````html```, it is not needed.
        - no table! Start with the title <h3>
        - if there are conclusions, put them in normal <p> tags. No <h1> or <h2> tags
        
        Finally, be sure that everything is formatted in HTML, e.g. all paragraphs in <p> tags.
        """
        # Check if llm_model is defined, otherwise set a default value
        if 'llm_model' not in globals() or llm_model is None:
            model = "Meta-Llama-3-8B"
            set_global_llm_model(model, verbose=True)

        ai_response = chat(chatbot_prompt, llm_model)
        model = get_model_name_from_llm(llm_model)

    print(f"RESPONSE\n{ai_response}")
    
    return render_template('stop.html', stop_name=stop_name, description=description, ai_response=ai_response, 
                           llm=model)


@app.route('/question', methods=['POST'])
def question_with_ai():
    user_message = request.json.get('message')
    model = request.json.get('new_llm')
    
    print(f"\nuser_message: {user_message}")
    print(f"llm_model: {model}")
    set_global_llm_model(model, verbose=True)
    prompt = f"""
    This is the message from the user: {user_message}.
    This is the page they are on: {request.referrer}.
    ## Instructions:
    - do not use the page to get the answer to the user question, this is just a context for you
    - be clear
    - provide some insightful answer
    - do not repeat the question
    - divide your answer in short and catchy paragraphs
    IMPORTANT: format the answer in HTML! But do not add ```html``` or stuff like that. Go directly to the <p>
    """

    response = chat(prompt, llm_model)

    print(f"\nRESPONSE\n{response}\n")

    return jsonify({'response': response})



def set_global_llm_model(model, verbose=False):

    global llm_model
    
    if model == "Llama-3.3-70B":
        llm_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
    elif model == "Meta-Llama-3-8B":
        llm_model = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
    elif model == 'DeepSeek-R1':
        llm_model = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"
    elif model == 'gemini-2.0-flash':
        llm_model = "gemini-2.0-flash"
    else:
        raise ValueError("Model not found")
    
    if verbose:
        print(f"Model set to: {llm_model}")
    
    global client
    if "meta" in llm_model or "deepseek" in llm_model:
        client = Together(api_key=meta_api_key)
    elif "gemini" in llm_model:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        client = genai.Client(api_key=gemini_api_key)
    else:
        raise ValueError("Model not found")
    
def get_model_name_from_llm(llm_model):
    mapping = {
        "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free": "Llama-3.3-70B",
        "meta-llama/Meta-Llama-3-8B-Instruct-Lite": "Meta-Llama-3-8B",
        "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free": "DeepSeek-R1",
        "gemini-2.0-flash": "gemini-2.0-flash"
    }

    if llm_model in mapping:
        return mapping[llm_model]
    else:
        raise ValueError("LLM model string not recognized")
        
def generate_ai_itinerary(city, interests, duration, pace, 
                          tryout=False, verbose=False):
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
    start = datetime.now()
    if tryout:
        from test.test import final_draft_test, list_of_stops_test

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
        if verbose:
            print(f'\nper stops: {stops}\n')
        stops = stops.split(':')[-1]
        if verbose:
            print(f'\npost stops: {stops}\n')

    end = datetime.now()
    if verbose:
        print(f"\nLLM Model: {llm_model}\nTime taken: {end-start}\n")
    return final_draft, stops

def generate_revised_ai_itinerary(feedback, 
                                  old_itinerary, old_stops,
                                  city, interests, duration, pace, 
                                  tryout=False, verbose=False):
    '''
    main AI place
    '''

    start = datetime.now()
    if tryout:
        
        final_draft = final_draft_test
        stops = list_of_stops_test

    else:
        # 1. get city weather
        weather = get_city_weather(city)
    
        # 2. generate new_first_draft
        new_first_draft = generate_new_first_draft(feedback, old_itinerary, old_stops, city, interests, duration, pace, weather)
    
        # 3. get_stops
        stops_0 = get_stops(new_first_draft)
    
        # 4. validate_stops
        stops = validate_stops(stops_0, city)
        stops = stops.replace('&', 'and')
    
        # 5. format itinerary
        final_draft = format_new_itinerary(new_first_draft, stops, city, interests, duration, pace, weather,
                                           feedback, old_itinerary, old_stops)
        if verbose:
            print(f'\nper stops: {stops}\n')
        stops = stops.split(':')[-1]
        if verbose:
            print(f'\npost stops: {stops}\n')

    end = datetime.now()
    if verbose:
        print(f"\nLLM Model: {llm_model}\nTime taken: {end-start}\n")
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

    response = chat(chatbot_prompt, llm_model)

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

    response = chat(chatbot_prompt, llm_model)

    return response

def generate_new_first_draft(feedback, old_itinerary, old_stops, city, interests, duration, pace, weather):
    
    chatbot_prompt = f"""
    You are a local tour guide in {city} helping tourists to find the best places to visit.
    They have these interests: {interests}.
    They want to visit the city with this pace: {pace}; and in this time: {duration} days. 
    Also, the weather in the city is {weather}.
    
    You already gave them an itinerary, but they want to change it.
    Here is the old itinerary: {old_itinerary}
    Here is the old list of stops: {old_stops}
    Here is the feedback from the tourists: {feedback}
    So adapt your answers to it.

    ## Instructions:
    * adapt your answer to the city, interests, duration, pace, and weather
    * be as thorough as possible. Don't leave behind any details
    * Give a detailed verbose response
    * add a precise list of stops
    * stick to the feedback from the tourists
    * don't include the old itinerary in your response
    * don't include the old list of stops in your response
    """

    response = chat(chatbot_prompt, llm_model)

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

    response = chat(chatbot_prompt, llm_model)

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

    response = chat(chatbot_prompt, llm_model)

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
            <li>
                <strong>10:00 AM:</strong> Visit the main attractions. 
                <a href="/stop/Main%20attraction?description=the%20main%20attraction%20is%20this%2and%20that." target="_blank">
                    More info
                </a>.
            </li>
            <li>
                <strong>2:00 PM:</strong> Explore local cuisine.
                <a href="/stop/local%20restaurant?description=description%20of%20the%20local%20restaurant." target="_blank">
                    More info
                </a>.
            </li>
            <li>
                <strong>6:00 PM:</strong> Evening entertainment.
                <a href="/stop/evening%entertainment?description=description%20of%20the%20evening%20entertainment." target="_blank">
                    More info
                </a>.
            </li>
        </ul>
        <h4>Useful Tips:</h4>
        <ul>
            <li>something about the weather</li>
            <li>Wear comfortable shoes</li>
            <li>Bring a camera</li>
        </ul>
    </div>
    '

    Be sure to include - for each stop described - a link to the stop page with a description of the stop as per example above. Substitute the example description with a brief description of the stop.
    """

    final_draft = chat(chatbot_prompt, llm_model)

    return final_draft


def format_new_itinerary(first_draft, stops, city, interests, duration, pace, weather,
                         feedback, old_itinerary, old_stops):                                           

    chatbot_prompt = f"""
    You are a local tour guide in {city} helping tourists to find the best places to visit.
    You already gave them an itinerary, but they want to change it.
    Here is the old itinerary: {old_itinerary} and the old list of stops: {old_stops}.
    Here is the feedback from the tourists: {feedback}.
    
    Read the new first draft - {first_draft} - and the list of new stops - {stops} - and write a complete response.
    Compare them with the old itinerary and stops and include the changes in your response. Be sure you follow the feedback from the tourists.
    Include information about the weather: {weather}.

    Keep also in mind that:
    - They have these interests: {interests}.
    - They want to visit the city with this pace: {pace}; 
    - They want to visit the city in this time: {duration}. 
    

    # Instructions:
    - prioritize the feedback from the tourists
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
            <li>
                <strong>10:00 AM:</strong> Visit the main attractions. 
                <a href="/stop/Main%20attraction?description=the%20main%20attraction%20is%20this%2and%20that." target="_blank">
                    More info
                </a>.
            </li>
            <li>
                <strong>2:00 PM:</strong> Explore local cuisine.
                <a href="/stop/local%20restaurant?description=description%20of%20the%20local%20restaurant." target="_blank">
                    More info
                </a>.
            </li>
            <li>
                <strong>6:00 PM:</strong> Evening entertainment.
                <a href="/stop/evening%entertainment?description=description%20of%20the%20evening%20entertainment." target="_blank">
                    More info
                </a>.
            </li>
        </ul>
        <h4>Useful Tips:</h4>
        <ul>
            <li>something about the weather</li>
            <li>Wear comfortable shoes</li>
            <li>Bring a camera</li>
        </ul>
    </div>
    '

    Be sure to include - for each stop described - a link to the stop page with a description of the stop as per example above.
    Substitute the example description with a brief description of the stop.
    """

    final_draft = chat(chatbot_prompt, llm_model)

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

def chat(prompt, model):
    
    if 'meta' in model or 'deepseek' in model:
        response = client.chat.completions.create(model=llm_model,
                                                  messages=[{"role": "user", "content": prompt}],)
        output = response.choices[0].message.content

    elif 'gemini' in model:
        response = client.models.generate_content(model=llm_model,
                                                  contents=prompt)
        output = response.text
    
    else:
        raise ValueError("Model not found")

    return output

# other useful functions

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
    app.run(debug=True)