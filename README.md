# 🌍 AI Travel Planner + Chatbot

An AI-powered travel planner that generates personalized itineraries, shows live weather, displays destination images, and includes a chatbot for answering travel-related queries.

## 🚀 Features
- AI-based trip itinerary generation (day-wise plan, budget, tips)  
- Context-aware chatbot for follow-up questions  
- Live weather data using OpenWeather API  
- Destination images using Pexels API  
- Smart fallback system when AI quota is exhausted  
- Caching and retry logic for handling API failures  

## 🛠️ Tech Stack
- Python  
- Streamlit  
- Gemini API (Google GenAI)  
- OpenWeather API  
- Pexels API  

## ▶️ How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
2. Add your API keys in .streamlit/secrets.toml:
GEMINI_API_KEY = "your_key"
OPENWEATHER_API_KEY = "your_key"
PEXELS_API_KEY = "your_key"

3.Run the app:
python -m streamlit run app.py
