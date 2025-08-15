# 🎤 AI Voice Agent - 30 Days Challenge Project

> A sophisticated conversational AI voice agent built over 30 days, featuring real-time speech processing, intelligent responses, and natural voice synthesis.

![AI Voice Agent](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Live Demo

Experience the power of conversational AI with just one click! Speak naturally, and the agent responds with intelligence and personality.

![AI Voice Agent Demo](demo-screenshot.png)

## 📖 Project Overview

This AI Voice Agent represents the culmination of a 12-day intensive development journey, transforming from a simple text-to-speech tool into a fully conversational AI assistant. The agent can:

- **Listen** to your voice with high-accuracy transcription
- **Think** using advanced large language models
- **Remember** conversation context across multiple turns
- **Respond** with natural, human-like speech
- **Handle** errors gracefully with intelligent fallbacks

### 🎯 Key Features

#### 🎙️ **Advanced Voice Processing**
- Real-time audio recording via browser MediaRecorder API
- Professional-grade speech-to-text using AssemblyAI
- Crystal-clear voice synthesis with Murf AI voices

#### 🧠 **Intelligent Conversations**
- Powered by Google Gemini 1.5 Flash LLM
- Persistent conversation memory per session
- Context-aware responses and follow-up handling

#### 🎨 **Modern User Interface**
- Glassmorphism design with gradient backgrounds
- Smart button that adapts to conversation state
- Animated visual feedback and audio visualizers
- Fully responsive mobile and desktop experience

#### 🛡️ **Production-Ready Features**
- Comprehensive error handling and fallback systems
- Automatic conversation continuation
- Session management with URL-based persistence
- API rate limiting and timeout protection


### Technology Stack

#### 🖥️ **Backend**
- **FastAPI** - High-performance async web framework
- **Python 3.8+** - Core programming language
- **AssemblyAI SDK** - Speech-to-text transcription
- **Google Gemini API** - Large language model intelligence
- **Murf AI SDK** - Natural voice synthesis
- **Uvicorn** - ASGI server for production deployment

#### 🎨 **Frontend**
- **HTML5** - Semantic markup and audio handling
- **CSS3** - Modern styling with animations and gradients
- **Vanilla JavaScript** - MediaRecorder API and async operations
- **Jinja2** - Server-side template rendering

#### 🔧 **Development Tools**
- **python-dotenv** - Environment variable management
- **CORS Middleware** - Cross-origin request handling
- **Logging** - Comprehensive error tracking and debugging


## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Modern web browser with microphone access
- API keys for AssemblyAI, Google Gemini, and Murf AI

### 1. Clone the Repository

### 2. Install Dependencies

### 3. Environment Configuration
Create a `.env` file in the root directory with your API keys:

MURF_API_KEY=your_murf_api_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
GEMINI_API_KEY=your_google_gemini_api_key_here

### 4. Run the Application

The application will be available at `http://localhost:8000`

## 🔑 API Keys Setup

### AssemblyAI
1. Sign up at [AssemblyAI Dashboard](https://www.assemblyai.com/dashboard/signup)
2. Copy your API key from the dashboard
3. Add to `.env` file as `ASSEMBLYAI_API_KEY`

### Google Gemini
1. Visit [Google AI Studio](https://ai.google.dev/gemini-api/docs/quickstart)
2. Create a new project and generate API key
3. Add to `.env` file as `GEMINI_API_KEY`

### Murf AI
1. Create account at [Murf AI](https://murf.ai/)
2. Navigate to API section for your key
3. Add to `.env` file as `MURF_API_KEY`

## 🚀 Usage

### Basic Conversation
1. **Open** the application in your browser
2. **Click** the microphone button to start recording
3. **Speak** your message clearly
4. **Click** again to stop recording
5. **Listen** as the AI processes and responds

### Advanced Features
- **Session Persistence**: Each conversation maintains context via session IDs
- **Auto-Continuation**: Agent automatically listens after responding
- **Error Recovery**: Intelligent fallbacks when services are unavailable
- **Mobile Support**: Full functionality on mobile devices

## 📡 API Endpoints

### Core Endpoints
- `GET /` - Main web interface
- `POST /agent/chat/{session_id}` - Primary conversational endpoint
- `POST /generate-audio/` - Text-to-speech generation
- `POST /transcribe/file` - Audio transcription service
- `GET /health` - Service health check

### Response Format
{
"audio_url": "https://example.com/generated-audio.mp3"
}
## 🛠️ Development Journey

This project was built incrementally over 12 days:

- **Day 1-2**: Project setup and basic TTS integration
- **Day 3-4**: Frontend development and audio recording
- **Day 5-6**: Server-side audio processing and transcription
- **Day 7-8**: LLM integration and echo bot functionality
- **Day 9-10**: Full conversational pipeline and chat history
- **Day 11-12**: Error handling and modern UI design

## 🔧 Troubleshooting

### Common Issues

**Microphone Access Denied**
- Ensure browser permissions allow microphone access
- Use HTTPS in production for security requirements

**API Rate Limits**
- Monitor usage across all three API services
- Implement exponential backoff for retries

**Audio Playback Issues**
- Check browser audio codecs support
- Verify network connectivity for streaming

### Debug Mode
Enable detailed logging by running:

## 🌟 Future Enhancements

- **Multi-language Support** - Expand beyond English conversations
- **Voice Cloning** - Custom voice profiles for personalization
- **Real-time Streaming** - Reduce latency with streaming STT/TTS
- **Database Integration** - Persistent conversation storage
- **User Authentication** - Secure personal conversation history

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and enhancement requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Special thanks to:
- **[Murf AI](https://murf.ai/)** for organizing the 30 Days Challenge
- **[AssemblyAI](https://www.assemblyai.com/)** for powerful speech recognition
- **[Google](https://ai.google.dev/)** for Gemini API access
- The amazing developer community for inspiration and support

---

⭐ **Star this repo if you found it helpful!** 

📧 **Questions?** Open an issue or reach out on LinkedIn!

🎯 **Challenge completed**: 13/30 days • 🏆 **Next milestone**: Advanced features and optimizations

---

*Built with ❤️ during the #30DaysofVoiceAgents challenge • #BuildwithMurf*
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
assemblyai==0.21.0
murf==1.0.0
jinja2==3.1.2
python-multipart==0.0.6
# Environment variables
.env

# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual environment
venv/
env/
ENV/

# Upload files
uploads/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db
