import os
import re
import time
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

# -------------------------------
# Helper functions
# -------------------------------
def call_gemini_with_retry(client, prompt):
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait_time = 2 + attempt
                time.sleep(wait_time)
            else:
                return f"Error: {str(e)}"

    return "⚠️ AI servers are busy right now. Please try again in a few seconds."

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

def get_suggested_places_with_gemini(destination: str, days: int, travel_style: str):
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
Suggest the top {min(days * 3, 6)} tourist places to visit in {destination}
for a {travel_style} trip.

Rules:
1. Return only place names
2. One place per line
3. Do not add numbering
4. Do not add explanation
5. Do not add bullets
"""

    places_text = call_gemini_with_retry(client, prompt).strip()
    places = [line.strip().lstrip("-•1234567890. ") for line in places_text.split("\n") if line.strip()]
    return places[:6]

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

Instructions:
1. Give a short introduction.
2. Create a day-wise itinerary.
3. Suggest top places to visit.
4. Give a rough budget split for stay, food, travel, and activities.
5. Mention weather-aware travel tips.
6. Mention what to pack.
7. Keep the answer clear, simple, and nicely formatted.
8. Do not invent flights or hotel bookings.
"""

    return call_gemini_with_retry(client, prompt)

def ask_trip_chatbot(user_question: str):
    if not st.session_state.plan_text:
        return "Please generate a trip plan first."

    client = genai.Client(api_key=GEMINI_API_KEY)

    destination = st.session_state.trip_context.get("destination", "")
    days = st.session_state.trip_context.get("days", "")
    budget = st.session_state.trip_context.get("budget", "")
    travel_style = st.session_state.trip_context.get("travel_style", "")
    companions = st.session_state.trip_context.get("companions", "")
    weather = st.session_state.trip_context.get("weather", {})

    history_text = ""
    if st.session_state.chat_history:
        for item in st.session_state.chat_history:
            history_text += f"User: {item['user']}\nAssistant: {item['assistant']}\n"

    weather_summary = (
        f"Temperature: {weather.get('temperature')}°C, "
        f"Condition: {weather.get('weather_desc')}, "
        f"Humidity: {weather.get('humidity')}%, "
        f"Wind speed: {weather.get('wind_speed')} m/s"
    )

    prompt = f"""
You are a travel chatbot helping a user with the same trip.

Trip details:
Destination: {destination}
Days: {days}
Budget: {budget}
Travel Style: {travel_style}
Companions: {companions}
Weather: {weather_summary}

Original Trip Plan:
{st.session_state.plan_text}

Previous Chat History:
{history_text}

Answer the user's latest question in a helpful, short, practical way.

Latest User Question:
{user_question}
"""

    return call_gemini_with_retry(client, prompt)

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

                    plan_text = generate_trip_plan_with_gemini(
                        destination=destination,
                        days=days,
                        budget=budget,
                        travel_style=travel_style,
                        companions=companions,
                        weather=weather,
                        extra_notes=extra_notes
                    )

                    suggested_places = get_suggested_places_with_gemini(destination, days, travel_style)

                    st.session_state.plan_text = plan_text
                    st.session_state.trip_context = {
                        "destination": destination,
                        "days": days,
                        "budget": budget,
                        "travel_style": travel_style,
                        "companions": companions,
                        "weather": weather
                    }
                    st.session_state.suggested_places = suggested_places
                    st.session_state.chat_history = []

                    st.success("Trip plan generated successfully!")

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

    st.subheader("🗺️ AI Trip Plan")
    st.markdown(st.session_state.plan_text)

    st.subheader("📸 Itinerary Highlights")

    if suggested_places:
        for place in suggested_places[:5]:
            st.markdown('<div class="place-card">', unsafe_allow_html=True)

            place_image = get_destination_image(place, PEXELS_API_KEY)

            col1, col2 = st.columns([1.2, 2.8])

            with col1:
                if place_image and place_image.get("image_url"):
                    st.image(place_image["image_url"], width=240)
                else:
                    st.info("No image")

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
