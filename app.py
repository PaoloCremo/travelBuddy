from flask import Flask, render_template, request, jsonify
import random

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
        
        return render_template('itinerary.html', itinerary=itinerary, city=city, duration=duration)
    return render_template('create_itinerary.html')

def generate_ai_itinerary(city, interests, duration, pace):
    # Mock AI function to generate itinerary
    activities = [
        "Visit the local museum",
        "Explore the city center",
        "Try local cuisine at a popular restaurant",
        "Relax in a nearby park",
        "Take a guided city tour",
        "Shop at the local market",
        "Attend a cultural event",
        "Visit historical landmarks"
    ]
    
    itinerary = []
    for day in range(1, duration + 1):
        daily_activities = random.sample(activities, 3 if pace == 'moderate' else (2 if pace == 'relaxed' else 4))
        itinerary.append({
            'day': day,
            'activities': daily_activities
        })
    
    return itinerary

if __name__ == '__main__':
    app.run(debug=False)
