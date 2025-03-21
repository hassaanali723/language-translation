# Language Translation API

A robust, enterprise-level language translation API built with FastAPI and LibreTranslate.

## Features

- Text translation between multiple languages
- Language detection
- Caching with Redis
- Circuit breaker pattern for reliability
- Structured logging
- Rate limiting

## Tech Stack

- FastAPI
- LibreTranslate
- Redis
- Docker
- Python 3.8+

## Setup

1. Clone the repository:
```bash
git clone https://github.com/hassaanali723/language-translation.git
cd language-translation
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Start Redis:
```bash
docker run --name redis -p 6379:6379 -d redis
```

4. Start LibreTranslate:
```bash
docker run -it -p 5500:5000 libretranslate/libretranslate
```

5. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

Create a `.env` file in the root directory with the following variables:
```env
LIBRE_TRANSLATE_URL=http://localhost:5500
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

## Project Structure

```
app/
├── api/
│   └── v1/
│       └── endpoints/
│           └── translation.py
├── core/
│   ├── config.py
│   ├── logging.py
│   └── rate_limit.py
├── services/
│   ├── cache/
│   │   └── redis_cache.py
│   └── translation/
│       ├── base.py
│       └── libre_translate.py
└── schemas/
    └── translation.py
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 