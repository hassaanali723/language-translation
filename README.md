# Language Translator with TTS Support

A comprehensive language translation service with text-to-speech capabilities. Built with FastAPI, this application provides translation between multiple languages and high-quality text-to-speech conversion supporting 100+ languages.

## Features

### Translation
- Text translation between multiple languages
- Language detection
- Batch translation support
- File translation (.txt, .docx, etc.)
- Translation memory and caching
- Rate limiting and usage tracking

### Text-to-Speech (TTS)
- Speech synthesis in 100+ languages
- Streaming audio file support
- Configurable speech parameters (speed, pitch, volume)
- MP3 audio format
- Clean service-based architecture

### General Features
- RESTful API using FastAPI
- Swagger/OpenAPI documentation
- Redis caching
- Prometheus metrics
- Structured logging
- Environment-based configuration

## Requirements

- Python 3.8+
- FastAPI
- Redis
- gTTS (Google Text-to-Speech)
- Other dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd language-translator
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start Redis:
```bash
docker run --name redis -p 6379:6379 -d redis
```

5. Create a `.env` file with your configuration:
```env
# Server Settings
HOST=0.0.0.0
PORT=8000
WORKERS=1
LOG_LEVEL=info

# Storage
AUDIO_STORAGE_PATH=./audio_files

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

## Usage

1. Start the server:
```bash
uvicorn main:app --reload
```

2. Access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Translation

#### Translate Text
```http
POST /api/v1/translate
```

Request body:
```json
{
    "text": "Hello, how are you?",
    "source_lang": "en",
    "target_lang": "es"
}
```

Response:
```json
{
    "translated_text": "Hola, ¿cómo estás?",
    "source_lang": "en",
    "target_lang": "es",
    "confidence": 0.92
}
```

#### Detect Language
```http
POST /api/v1/translate/detect
```

Request body:
```json
{
    "text": "Hello, how are you?"
}
```

Response:
```json
{
    "detected_lang": "en",
    "confidence": 0.98
}
```

#### Translate File
```http
POST /api/v1/translate/file
```

Form data:
- `file`: File to translate
- `source_lang`: Source language code
- `target_lang`: Target language code

Response: Translated file download

### Text-to-Speech

#### Convert Text to Speech
```http
POST /api/v1/tts/convert
```

Request body:
```json
{
    "text": "Hello, how are you?",
    "language": "en",
    "speed": 1.0,
    "pitch": null,
    "volume": null
}
```

Response:
```json
{
    "success": true,
    "audio_file_name": "uuid.mp3",
    "audio_file_url": "/api/v1/tts/audio/uuid",
    "language": "en"
}
```

#### Get Audio File
```http
GET /api/v1/tts/audio/{file_id}
```

Returns the audio file as a streaming response.

## Project Structure

```
language-translator/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── translate.py
│   │           └── tts.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── metrics.py
│   ├── schemas/
│   │   ├── translate.py
│   │   └── tts.py
│   └── services/
│       ├── translation/
│       │   ├── base.py
│       │   └── translator.py
│       └── tts/
│           ├── base.py
│           └── gtts_service.py
├── tests/
│   ├── api/
│   ├── services/
│   └── conftest.py
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── main.py
└── README.md
```

## Monitoring and Metrics

The application exposes Prometheus metrics at `/metrics` endpoint, including:
- Request counts and latencies
- Translation and TTS service metrics
- Cache hit/miss ratios
- Rate limiting statistics

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages:
- 400: Bad Request (invalid input)
- 404: Not Found
- 429: Too Many Requests (rate limit exceeded)
- 500: Internal Server Error

Error response format:
```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Detailed error message",
        "details": {}
    }
}
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

MIT License - see the [LICENSE](LICENSE) file for details. 
