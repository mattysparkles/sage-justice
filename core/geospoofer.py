import random

def get_random_location():
    locations = [
        {"city": "New York", "lat": 40.7128, "lon": -74.0060},
        {"city": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
        {"city": "Chicago", "lat": 41.8781, "lon": -87.6298},
        {"city": "Houston", "lat": 29.7604, "lon": -95.3698},
        {"city": "Phoenix", "lat": 33.4484, "lon": -112.0740}
    ]
    return random.choice(locations)

def spoof_location(driver, location):
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "accuracy": 100
    }
    driver.execute_cdp_cmd("Emulation.setGeolocationOverride", params)
