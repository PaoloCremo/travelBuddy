@app.route('/create_itinerary', methods=['GET', 'POST'])
def create_itinerary():
    if request.method == 'POST':
        # Get form data
        city = request.form.get('city')
        interests = request.form.get('interests')
        duration = request.form.get('duration')
        pace = request.form.get('pace')
        
        # In a real app, we would call our AI agents here
        # For now, we'll use mock data
        places = generate_places_recommendations(city, interests, pace)
        restaurants = generate_restaurant_recommendations(city, interests)
        
        return render_template('itinerary.html', 
                              city=city, 
                              interests=interests,
                              duration=duration,
                              pace=pace,
                              places=places,
                              restaurants=restaurants)
    
    return render_template('create_itinerary.html')

def generate_places_recommendations(city, interests, pace):
    # Mock function - in a real app, this would call a Places API like Geoapify
    # This would be handled by our AI agents
    if city.lower() == 'paris':
        return [
            {"name": "Louvre Museum", "description": "World's largest art museum", "category": "Art"},
            {"name": "Eiffel Tower", "description": "Iconic iron tower", "category": "Landmark"},
            {"name": "Notre-Dame Cathedral", "description": "Medieval Catholic cathedral", "category": "Historical"}
        ]
    else:
        return [
            {"name": "Local Museum", "description": "City's main museum", "category": "Art"},
            {"name": "City Park", "description": "Beautiful urban park", "category": "Nature"},
            {"name": "Historic District", "description": "Old town with historic buildings", "category": "Historical"}
        ]

def generate_restaurant_recommendations(city, interests):
    # Mock function - in a real app, this would call a Restaurant API
    if city.lower() == 'paris':
        return [
            {"name": "Le Petit Bistro", "cuisine": "French", "price_level": "$$"},
            {"name": "Café de Paris", "cuisine": "French", "price_level": "$$$"},
            {"name": "La Boulangerie", "cuisine": "Bakery", "price_level": "$"}
        ]
    else:
        return [
            {"name": "Local Diner", "cuisine": "Traditional", "price_level": "$$"},
            {"name": "City Grill", "cuisine": "Steakhouse", "price_level": "$$$"},
            {"name": "Corner Café", "cuisine": "Café", "price_level": "$"}
        ]