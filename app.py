import os
import re
import time
import random
import requests
import streamlit as st
from google import genai

# -------------------------------
# Page setup
# -------------------------------
st.set_page_config(
    page_title="AI Travel Planner + Chatbot",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 AI Travel Planner + Chatbot")
st.markdown(
    "<p style='text-align:center; font-size:20px; color:#cbd5e1;'>Plan a trip, see live weather, view destination images, and chat with your travel assistant.</p>",
    unsafe_allow_html=True
)
st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
<style>

/* Full app background */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #111827 45%, #1e293b 100%);
    color: #e2e8f0 !important;
}

/* Force text color */
html, body, p, span, label, div, li {
    color: #e2e8f0 !important;
}

/* Make cursor visible */
html, body, .stApp, button, input, textarea, select {
    cursor: auto !important;
}

.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    caret-color: #f8fafc !important;
}

/* Top header bar */
header {
    background: transparent !important;
}

[data-testid="stHeader"] {
    background: rgba(15, 23, 42, 0.85) !important;
}

/* Main content area */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1050px !important;
}

/* Main title */
h1 {
    color: #f8fafc !important;
    font-size: 3rem !important;
    font-weight: 800 !important;
    text-align: center;
    margin-bottom: 0.5rem;
}

/* Section headings */
h2, h3, h4 {
    color: #cbd5e1 !important;
    font-weight: 700 !important;
}

/* Paragraph under heading */
.stMarkdown p {
    color: #cbd5e1 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #0f172a 100%) !important;
    border-right: 1px solid #334155;
}

/* Sidebar text */
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    background-color: #1e293b !important;
    color: #f8fafc !important;
    border: 1.5px solid #475569 !important;
    border-radius: 14px !important;
}

/* Number input buttons area */
.stNumberInput div[data-baseweb="input"] {
    background-color: #1e293b !important;
    border-radius: 14px !important;
    border: 1.5px solid #475569 !important;
}

/* Selectbox outer box */
div[data-baseweb="select"] > div {
    background-color: #1e293b !important;
    border: 1.5px solid #475569 !important;
    border-radius: 14px !important;
    color: #f8fafc !important;
}

/* Selectbox value text */
div[data-baseweb="select"] span {
    color: #f8fafc !important;
}

/* Dropdown menu */
ul[role="listbox"] {
    background-color: #1e293b !important;
    border: 1px solid #475569 !important;
    border-radius: 12px !important;
}

/* Dropdown options */
ul[role="listbox"] li {
    background-color: #1e293b !important;
    color: #f8fafc !important;
}

/* Button */
.stButton > button {
    background: linear-gradient(135deg, #334155 0%, #475569 100%) !important;
    color: #f8fafc !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 0.75rem 1.4rem !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}

.stButton > button:hover {
    background: linear-gradient(135deg, #475569 0%, #64748b 100%) !important;
    color: white !important;
}

/* Metrics */
div[data-testid="metric-container"] {
    background: #1e293b !important;
    border: 1.5px solid #475569 !important;
    border-radius: 16px !important;
    padding: 14px !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
}

/* Image/place cards */
.place-card {
    background: rgba(30, 41, 59, 0.96);
    border: 1.5px solid #475569;
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 18px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

/* Small spacing improvement */
hr {
    border-color: #475569 !important;
}

/* Hide Streamlit footer/menu clutter a bit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

</style>
""", unsafe_allow_html=True)

# -------------------------------
# API keys from Streamlit secrets
# -------------------------------
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
OPENWEATHER_API_KEY = st.secrets["OPENWEATHER_API_KEY"]
PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]

# -------------------------------
# Session state
# -------------------------------
if "plan_text" not in st.session_state:
    st.session_state.plan_text = ""

if "trip_context" not in st.session_state:
    st.session_state.trip_context = {}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "suggested_places" not in st.session_state:
    st.session_state.suggested_places = []

if "plan_source" not in st.session_state:
    st.session_state.plan_source = ""

if "gemini_cache" not in st.session_state:
    st.session_state.gemini_cache = {}

# -------------------------------
# Helper functions
# -------------------------------
def is_quota_error(error_text: str) -> bool:
    text = error_text.upper()
    return (
        "429" in text or
        "RESOURCE_EXHAUSTED" in text or
        "QUOTA" in text or
        "RATE LIMIT" in text
    )

def safe_cache_key(prefix: str, *parts) -> str:
    return prefix + "::" + "::".join([str(p).strip().lower() for p in parts])

def fallback_trip_plan(
    destination: str,
    days: int,
    budget: str,
    travel_style: str,
    companions: str,
    weather: dict,
    extra_notes: str
) -> str:
    weather_line = (
        f"{weather.get('temperature', 'N/A')}°C, "
        f"{weather.get('weather_desc', 'weather details unavailable')}"
    )

    notes_line = extra_notes.strip() if extra_notes.strip() else "No extra preferences provided."

    itinerary_days = []
    for day in range(1, int(days) + 1):
        if day == 1:
            itinerary_days.append(
                f"**Day {day}: Arrival and local exploration**\n"
                f"- Reach {destination} and check in\n"
                f"- Explore nearby markets or a popular local area\n"
                f"- Keep the evening relaxed and adjust to the local weather"
            )
        elif day == int(days):
            itinerary_days.append(
                f"**Day {day}: Final sightseeing and departure**\n"
                f"- Visit one last nearby attraction\n"
                f"- Try local food or buy souvenirs\n"
                f"- Leave enough buffer time for checkout and return travel"
            )
        else:
            itinerary_days.append(
                f"**Day {day}: Main sightseeing day**\n"
                f"- Visit 2 to 3 major attractions\n"
                f"- Keep time for food, photos, and rest\n"
                f"- Plan indoor or outdoor stops depending on the weather"
            )

    return f"""
### Trip Overview
Here is a practical fallback itinerary for **{destination}** because the live AI quota is currently exhausted.

**Trip Duration:** {days} days  
**Budget:** {budget if str(budget).strip() else 'Not specified'}  
**Travel Style:** {travel_style}  
**Companions:** {companions}  
**Current Weather:** {weather_line}  
**Notes:** {notes_line}

### Day-wise Itinerary
{chr(10).join(itinerary_days)}

### Suggested Budget Split
- **Stay:** 35%
- **Food:** 20%
- **Local Travel:** 20%
- **Activities:** 15%
- **Buffer:** 10%

### What to Pack
- Comfortable clothes
- Walking shoes
- Phone charger and power bank
- Basic medicines
- Water bottle
- Weather-appropriate jacket or accessories

### Travel Tips
- Check local opening hours before visiting attractions
- Keep some extra time for traffic and queues
- Prefer local food at well-reviewed places
- Carry cash and digital payment options both

⚠️ The AI planner is temporarily unavailable because the Gemini quota has been reached. The app is using a fallback plan instead.
""".strip()

def fallback_places(destination: str, days: int):
    common_map = {
        "ladakh": ["Leh Palace", "Pangong Lake", "Nubra Valley", "Magnetic Hill", "Shanti Stupa", "Thiksey Monastery"],
        "goa": ["Baga Beach", "Calangute Beach", "Fort Aguada", "Dudhsagar Falls", "Anjuna Beach", "Basilica of Bom Jesus"],
        "manali": ["Solang Valley", "Hadimba Temple", "Old Manali", "Rohtang Pass", "Mall Road", "Vashisht Temple"],
        "jaipur": ["Hawa Mahal", "Amber Fort", "City Palace", "Jal Mahal", "Nahargarh Fort", "Jantar Mantar"],
        "shimla": ["Mall Road", "Kufri", "Jakhoo Temple", "The Ridge", "Christ Church", "Green Valley"]
    }

    key = destination.strip().lower()
    if key in common_map:
        return common_map[key][:min(days * 2, 6)]

    return [
        f"{destination} Main Market",
        f"{destination} City Center",
        f"{destination} Popular Viewpoint",
        f"{destination} Cultural Spot",
        f"{destination} Local Food Street",
        f"{destination} Nearby Scenic Place"
    ][:min(days * 2, 6)]

def fallback_chat_answer(user_question: str):
    q = user_question.strip().lower()

    if "pack" in q:
        return "Pack comfortable clothes, walking shoes, charger, power bank, ID, basic medicines, and weather-appropriate items."
    
    if "budget" in q or "cost" in q or "cheap" in q:
        return "Keep your budget split between stay, food, transport, activities, and a small emergency buffer. Book early for better prices."
    
    if "weather" in q:
        return "Please check the live weather card shown in the app and plan clothes, footwear, and sightseeing timing accordingly."
    
    if "food" in q or "eat" in q:
        return "Try popular local dishes, but prefer hygienic and well-reviewed places, especially during travel."
    
    if "places" in q or "visit" in q:
        return "You can use the itinerary highlights section for suggested places and prioritize the ones closest to your stay."

    return "I can help with your trip using the itinerary, weather details, and suggested places already shown above. Ask about packing, budget, places to visit, food, or weather."

def call_gemini_with_retry(client, prompt, cache_key=None, max_retries=4):
    if cache_key and cache_key in st.session_state.gemini_cache:
        return st.session_state.gemini_cache[cache_key]

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            text = getattr(response, "text", None)
            if text and text.strip():
                final_text = text.strip()
                if cache_key:
                    st.session_state.gemini_cache[cache_key] = final_text
                return final_text

            return None

        except Exception as e:
            error_text = str(e)

            if is_quota_error(error_text):
                return {
                    "type": "quota_error",
                    "message": "Gemini quota exhausted"
                }

            transient_signals = ["503", "UNAVAILABLE", "500", "DEADLINE_EXCEEDED", "INTERNAL"]
            if any(signal in error_text.upper() for signal in transient_signals) and attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
                continue

            return {
                "type": "other_error",
                "message": error_text
            }

    return {
        "type": "other_error",
        "message": "AI servers are busy right now. Please try again later."
    }

def get_city_coordinates(city: str, api_key: str):
    url = "https://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city,
        "limit": 1,
        "appid": api_key
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    if not data:
        return None

    return {
        "name": data[0].get("name", city),
        "country": data[0].get("country", ""),
        "lat": data[0].get("lat"),
        "lon": data[0].get("lon")
    }

def get_current_weather(lat: float, lon: float, api_key: str):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    weather_main = ""
    weather_desc = ""
    icon = ""

    weather_list = data.get("weather", [])
    if weather_list:
        weather_main = weather_list[0].get("main", "")
        weather_desc = weather_list[0].get("description", "")
        icon = weather_list[0].get("icon", "")

    return {
        "temperature": data.get("main", {}).get("temp"),
        "feels_like": data.get("main", {}).get("feels_like"),
        "humidity": data.get("main", {}).get("humidity"),
        "wind_speed": data.get("wind", {}).get("speed"),
        "weather_main": weather_main,
        "weather_desc": weather_desc,
        "icon": icon
    }

def get_destination_image(query: str, api_key: str):
    try:
        url = "https://api.pexels.com/v1/search"
        headers = {
            "Authorization": api_key
        }
        params = {
            "query": query,
            "per_page": 1,
            "orientation": "landscape"
        }

        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        photos = data.get("photos", [])
        if not photos:
            return None

        photo = photos[0]
        src = photo.get("src", {})
        image_url = src.get("large")

        if image_url:
            return {
                "image_url": image_url,
                "photographer": photo.get("photographer", "Pexels")
            }

        return None

    except Exception:
        return None

def generate_trip_plan_with_gemini(
    destination: str,
    days: int,
    budget: str,
    travel_style: str,
    companions: str,
    weather: dict,
    extra_notes: str
):
    client = genai.Client(api_key=GEMINI_API_KEY)

    weather_summary = (
        f"Temperature: {weather.get('temperature')}°C, "
        f"Feels like: {weather.get('feels_like')}°C, "
        f"Condition: {weather.get('weather_desc')}, "
        f"Humidity: {weather.get('humidity')}%, "
        f"Wind speed: {weather.get('wind_speed')} m/s"
    )

    prompt = f"""
You are a smart and practical travel planner.

Create a personalized trip plan based on the details below.

Destination: {destination}
Trip Duration: {days} days
Budget: {budget}
Travel Style: {travel_style}
Companions: {companions}
Current Weather: {weather_summary}
Extra Notes: {extra_notes}

Return the response in exactly this format:

TRIP_PLAN:
<write the full trip plan here with:
1. short introduction
2. day-wise itinerary
3. rough budget split
4. weather-aware travel tips
5. packing suggestions>

SUGGESTED_PLACES:
<place 1>
<place 2>
<place 3>
<place 4>
<place 5>
<place 6>

Rules:
- Do not number places
- One place per line under SUGGESTED_PLACES
- Keep output clean and structured
- Do not invent flights or hotel bookings
"""

    cache_key = safe_cache_key(
        "plan_with_places",
        destination,
        days,
        budget,
        travel_style,
        companions,
        weather_summary,
        extra_notes
    )

    result = call_gemini_with_retry(client, prompt, cache_key=cache_key)

    if isinstance(result, dict):
        fallback_plan = fallback_trip_plan(
            destination, days, budget, travel_style, companions, weather, extra_notes
        )
        fallback_places_list = fallback_places(destination, days)

        if result.get("type") == "quota_error":
            return fallback_plan, fallback_places_list, "fallback_quota", "fallback"

        return (
            "⚠️ The AI planner is temporarily unavailable due to a technical issue.\n\n" + fallback_plan,
            fallback_places_list,
            "fallback_error",
            "fallback"
        )

    if not result:
        return (
            fallback_trip_plan(destination, days, budget, travel_style, companions, weather, extra_notes),
            fallback_places(destination, days),
            "fallback_empty",
            "fallback"
        )

    plan_text = result
    suggested_places = []

    if "TRIP_PLAN:" in result and "SUGGESTED_PLACES:" in result:
        trip_part, places_part = result.split("SUGGESTED_PLACES:", 1)
        plan_text = trip_part.replace("TRIP_PLAN:", "", 1).strip()
        suggested_places = [
            line.strip().lstrip("-•1234567890. ")
            for line in places_part.split("\n")
            if line.strip()
        ]

    cleaned_places = []
    for place in suggested_places:
        if place and place not in cleaned_places:
            cleaned_places.append(place)

    if not cleaned_places:
        cleaned_places = fallback_places(destination, days)
        places_source = "fallback"
    else:
        places_source = "ai"

    return plan_text, cleaned_places[:6], "ai", places_source

def ask_trip_chatbot(user_question: str):
    if not st.session_state.plan_text:
        return "Please generate a trip plan first."

    destination = st.session_state.trip_context.get("destination", "")
    days = st.session_state.trip_context.get("days", "")
    budget = st.session_state.trip_context.get("budget", "")
    travel_style = st.session_state.trip_context.get("travel_style", "")
    companions = st.session_state.trip_context.get("companions", "")
    weather = st.session_state.trip_context.get("weather", {})
    suggested_places = st.session_state.suggested_places

    q = user_question.strip().lower()
    weather_desc = weather.get("weather_desc", "not available")
    temperature = weather.get("temperature", "N/A")
    humidity = weather.get("humidity", "N/A")
    wind_speed = weather.get("wind_speed", "N/A")

    if not q:
        return "Please ask a question."

    if "pack" in q or "packing" in q or "what should i carry" in q:
        return (
            f"For your {days}-day trip to {destination}, pack comfortable clothes, walking shoes, charger, "
            f"power bank, ID, basic medicines, and weather-appropriate items. Current weather is {temperature}°C with {weather_desc}, "
            f"so pack accordingly."
        )

    if "weather" in q or "temperature" in q or "rain" in q or "climate" in q:
        return (
            f"Current weather in {destination} is {temperature}°C with {weather_desc}. "
            f"Humidity is {humidity}% and wind speed is {wind_speed} m/s."
        )

    if "budget" in q or "cost" in q or "cheap" in q or "expensive" in q:
        return (
            f"Your selected budget is {budget if str(budget).strip() else 'not specified'}. "
            f"A practical split is: stay 35%, food 20%, local travel 20%, activities 15%, and 10% as buffer."
        )

    if "place" in q or "visit" in q or "where should i go" in q or "top attraction" in q:
        if suggested_places:
            return f"Top places you can prioritize in {destination}: " + ", ".join(suggested_places[:5]) + "."
        return f"You can explore popular attractions, local markets, scenic viewpoints, and food streets in {destination}."

    if "food" in q or "eat" in q or "restaurant" in q:
        return (
            f"For your trip to {destination}, try local food at hygienic and well-reviewed places. "
            f"Prefer popular local dishes and avoid risky food if you are travelling a lot during the day."
        )

    if "plan" in q or "itinerary" in q or "schedule" in q:
        return (
            "Your trip itinerary is already shown above in the AI Trip Plan section. "
            "You can follow the day-wise schedule there and adjust activities based on weather and energy level."
        )

    if "who am i travelling with" in q or "companions" in q:
        return f"You selected: {companions}."

    if "travel style" in q:
        return f"Your selected travel style is {travel_style}."

    return (
        f"This assistant is answering locally to save free-tier quota. "
        f"Your current trip is {days} days in {destination} with a {travel_style} style, travelling with {companions}. "
        f"You can ask about weather, packing, budget, places, food, or itinerary."
    )

# -------------------------------
# Sidebar
# -------------------------------
with st.sidebar:
    st.header("🔑 API Key Check")
    st.write(f"Gemini Key: {'✅ Found' if GEMINI_API_KEY else '❌ Missing'}")
    st.write(f"OpenWeather Key: {'✅ Found' if OPENWEATHER_API_KEY else '❌ Missing'}")
    st.write(f"Pexels Key: {'✅ Found' if PEXELS_API_KEY else '❌ Missing'}")
    st.markdown("---")
    st.subheader("About")
    st.write(
        "This project uses live APIs for weather and images, and Gemini for AI trip planning and chat."
    )

# -------------------------------
# Input form
# -------------------------------
st.subheader("🧳 Enter Trip Details")

col1, col2 = st.columns(2)

with col1:
    destination = st.text_input("Destination", placeholder="Goa")
    days = st.number_input("Trip Duration (days)", min_value=1, max_value=30, value=3)
    budget = st.text_input("Budget", placeholder="₹15000")

with col2:
    travel_style = st.selectbox(
        "Travel Style",
        ["Budget", "Luxury", "Adventure", "Family", "Romantic", "Relaxed"]
    )
    companions = st.selectbox(
        "Who are you travelling with?",
        ["Solo", "Friends", "Family", "Partner"]
    )
    extra_notes = st.text_area(
        "Extra Notes",
        placeholder="I prefer beaches, local food, and low-cost travel."
    )

generate_button = st.button("✨ Generate Trip Plan")

# -------------------------------
# Generate plan
# -------------------------------
if generate_button:
    if not destination.strip():
        st.error("Please enter a destination.")
    else:
        try:
            with st.spinner("Getting live data and building your trip plan..."):
                location_info = get_city_coordinates(destination, OPENWEATHER_API_KEY)

                if not location_info:
                    st.error("Could not find that destination. Try a different city name.")
                else:
                    weather = get_current_weather(
                        location_info["lat"],
                        location_info["lon"],
                        OPENWEATHER_API_KEY
                    )

                    plan_text, suggested_places, plan_source, places_source = generate_trip_plan_with_gemini(
                        destination=destination,
                        days=days,
                        budget=budget,
                        travel_style=travel_style,
                        companions=companions,
                        weather=weather,
                        extra_notes=extra_notes
                    )

                    st.session_state.plan_text = plan_text
                    st.session_state.plan_source = plan_source
                    st.session_state.trip_context = {
                        "destination": destination,
                        "days": days,
                        "budget": budget,
                        "travel_style": travel_style,
                        "companions": companions,
                        "weather": weather,
                        "places_source": places_source
                    }
                    st.session_state.suggested_places = suggested_places
                    st.session_state.chat_history = []

                    if plan_source == "ai":
                        st.success("Trip plan generated successfully!")
                    else:
                        st.warning("Trip plan loaded in fallback mode because AI quota is currently unavailable.")

        except requests.exceptions.RequestException as e:
            st.error(f"Network/API error: {e}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# -------------------------------
# Persistent plan display
# -------------------------------
if st.session_state.plan_text:
    destination_name = st.session_state.trip_context.get("destination", "")
    weather = st.session_state.trip_context.get("weather", {})
    suggested_places = st.session_state.suggested_places
    places_source = st.session_state.trip_context.get("places_source", "ai")

    st.subheader("🗺️ AI Trip Plan")

    if st.session_state.plan_source != "ai":
        st.info("AI quota reached, so the app is showing a fallback itinerary instead of a live Gemini-generated plan.")

    st.markdown(st.session_state.plan_text)

    st.subheader("📸 Itinerary Highlights")

    if places_source != "ai":
        st.caption("Suggested places are currently shown using fallback recommendations.")

    if suggested_places:
        for place in suggested_places[:5]:
            st.markdown('<div class="place-card">', unsafe_allow_html=True)

            place_image = get_destination_image(place, PEXELS_API_KEY)

            col1, col2 = st.columns([1.2, 2.8])

            with col1:
                if place_image and place_image.get("image_url"):
                    st.image(place_image["image_url"], width=240)
                else:
                    st.info("No image available")

            with col2:
                st.markdown(
                    f"""
                    <h3 style="
                        color:#f8fafc;
                        font-size:28px;
                        font-weight:700;
                        margin-top:20px;
                        margin-bottom:10px;
                    ">📍 {place}</h3>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <p style="
                        color:#cbd5e1;
                        font-size:17px;
                        margin-top:0;
                    ">
                    A beautiful place to explore during your trip in {destination_name}.
                    </p>
                    """,
                    unsafe_allow_html=True
                )

                if place_image:
                    st.markdown(
                        f"""
                        <p style="color:#94a3b8; font-size:14px;">
                        Image by {place_image.get('photographer', 'Unknown')} on Pexels
                        </p>
                        """,
                        unsafe_allow_html=True
                    )

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("No suggested places found.")

    st.subheader("🌦️ Live Weather")
    weather_col1, weather_col2, weather_col3, weather_col4 = st.columns(4)

    weather_col1.metric("Temperature", f"{weather.get('temperature', 'N/A')} °C")
    weather_col2.metric("Feels Like", f"{weather.get('feels_like', 'N/A')} °C")
    weather_col3.metric("Humidity", f"{weather.get('humidity', 'N/A')}%")
    weather_col4.metric("Wind", f"{weather.get('wind_speed', 'N/A')} m/s")

    st.write(
        f"**Condition:** {weather.get('weather_main', 'N/A')} ({weather.get('weather_desc', 'N/A')})"
    )

    st.markdown("---")
    st.subheader("💬 Travel Chatbot")

    with st.form("chat_form", clear_on_submit=True):
        user_question = st.text_input(
            "Ask a follow-up question",
            placeholder="What should I pack for this trip?"
        )
        ask_button = st.form_submit_button("Ask Chatbot")

    if ask_button:
        if not user_question.strip():
            st.warning("Please type a question.")
        else:
            try:
                with st.spinner("Thinking..."):
                    answer = ask_trip_chatbot(user_question)

                st.session_state.chat_history.append({
                    "user": user_question,
                    "assistant": answer
                })

            except Exception as e:
                st.error(f"Chatbot error: {e}")

    if st.session_state.chat_history:
        st.subheader("📝 Chat History")
        for i, item in enumerate(st.session_state.chat_history, start=1):
            st.markdown(f"**You {i}:** {item['user']}")
            st.markdown(f"**Bot {i}:** {item['assistant']}")
            st.markdown("---")
