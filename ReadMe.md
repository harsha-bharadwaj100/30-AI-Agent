# 🎤 AI Voice Agent - 30 Days Challenge Project

> A sophisticated conversational AI voice agent featuring real-time speech processing, intelligent responses, and a containerized architecture.

![AI Voice Agent](https://img.shields.io/badge/Status-Active-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Live Demo

Experience the power of conversational AI with just one click! Speak naturally, and the agent responds with intelligence and personality.

## 📖 Project Overview

This AI Voice Agent represents the culmination of a 30-day intensive development journey. It has evolved from a simple script into a robust, Dockerized application featuring:

- **Listen**: Real-time high-accuracy transcription (AssemblyAI).
- **Think**: Intelligent context processing (Google Gemini 1.5).
- **Speak**: Natural, human-like voice synthesis (Murf AI).
- **Deploy**: Runs anywhere via Docker.

### 🎯 Key Features

#### 🐳 **Dockerized & Privacy-First**
- Fully containerized application for zero-dependency setup.
- **Self-Hosted:** API keys remain on your local machine; no data is sent to a third-party backend server.

#### 🤖 **Distinct Persona ("Botto")**
- The agent is not just a bland bot; it possesses a witty, slightly sassy personality ("Botto") that adds character to interactions.

#### 🎙️ **Advanced Voice Processing**
- Real-time audio recording via browser MediaRecorder API.
- Crystal-clear voice synthesis with Murf AI voices.

#### 🧠 **Intelligent Conversations**
- Persistent conversation memory per session.
- Context-aware responses and follow-up handling.

#### 🛡️ **Production-Ready**
- Comprehensive error handling and fallback systems.
- Session management with URL-based persistence.

---

## ⚙️ Installation & Setup

You can run the agent using standard Python setup or, **recommended**, via Docker.

### Option A: 🐳 Run with Docker (Recommended)
Skip the dependency installation and run the agent immediately.

**1. Create your .env file**
Create a `.env` file in your folder with your keys:
```env
MURF_API_KEY=your_key
ASSEMBLYAI_API_KEY=your_key
GEMINI_API_KEY=your_key
2. Pull & Run

Bash

# Pull the latest image
docker pull harsha-bharadwaj100/voice-agent:latest

# Run the container (injecting your keys)
docker run -p 8000:8000 --env-file .env harsha-bharadwaj100/voice-agent:latest
Access the agent at http://localhost:8000

Option B: 🐍 Standard Python Setup
1. Clone the Repository

Bash

git clone [https://github.com/harsha-bharadwaj100/30-AI-Agent.git](https://github.com/harsha-bharadwaj100/30-AI-Agent.git)
cd 30-AI-Agent
2. Install Dependencies

Bash

pip install pipenv
pipenv install
3. Run the Application

Bash

pipenv run python main.py
🔑 API Keys Setup
AssemblyAI
Sign up at AssemblyAI Dashboard

Add to .env as ASSEMBLYAI_API_KEY

Google Gemini
Visit Google AI Studio

Add to .env as GEMINI_API_KEY

Murf AI
Create account at Murf AI

Add to .env as MURF_API_KEY

🛠️ Tech Stack
Containerization: Docker

Backend: FastAPI, Python 3.12, Uvicorn

AI Services: AssemblyAI (STT), Google Gemini (LLM), Murf AI (TTS)

Frontend: HTML5, Vanilla JS, CSS3 (Glassmorphism)

🤝 Contributing
Contributions are welcome! Please feel free to submit issues and enhancement requests.

Built with ❤️ during the #30DaysofVoiceAgents challenge • #BuildwithMurf