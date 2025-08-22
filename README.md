# TravelHelper 🌍✈️

A secure, AI-powered travel assistant web application built with Django that helps users plan trips, get travel advice, and answer travel-related questions using advanced language models.

## Features ✨

- **AI-Powered Chat**: Conversational interface powered by DeepSeek AI model via OpenRouter API
- **Travel Assistance**: Specialized travel advice, recommendations, and planning help
- **Conversation History**: Persistent chat sessions with message history
- **Security-First Design**: Comprehensive security measures including rate limiting, input validation, and CSRF protection
- **Production Ready**: Configured for AWS App Runner deployment with proper environment management
- **API-First Architecture**: RESTful API endpoints for easy integration

## Tech Stack 🛠️

- **Backend**: Django 4.2
- **Database**: MySQL (production) / SQLite (development)
- **AI/ML**: OpenRouter API with DeepSeek-chat-v3 model
- **Deployment**: AWS App Runner
- **Web Server**: Gunicorn with WhiteNoise for static files
- **Security**: Custom middleware for security headers, rate limiting, and input validation

## Quick Start 🚀

### Prerequisites

- Python 3.8+ (Note: Python 3.12+ users can ignore `backports.zoneinfo` installation errors as it's not needed)
- pip package manager
- MySQL database (for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jiangzizi/TravelHelper.git
   cd TravelHelper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` file with your configuration:
   ```bash
   SECRET_KEY=your-very-long-random-secret-key-here
   DEBUG=False
   DB_PASSWORD=your-database-password
   SOA_KEY=your-openrouter-api-key
   ```

4. **Database Setup**
   ```bash
   python manage.py migrate
   ```

5. **Run Security Check**
   ```bash
   python security_check.py
   ```

6. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

   Or for production:
   ```bash
   ./startup.sh
   ```

## Configuration ⚙️

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SECRET_KEY` | Django secret key for security | Yes | - |
| `DEBUG` | Enable debug mode | No | False |
| `DB_ENGINE` | Database engine | No | django.db.backends.mysql |
| `DB_NAME` | Database name | No | TRAVEL |
| `DB_USER` | Database username | No | admin |
| `DB_PASSWORD` | Database password | Yes | - |
| `DB_HOST` | Database host | No | localhost |
| `DB_PORT` | Database port | No | 3306 |
| `SOA_KEY` | OpenRouter API key | Yes | - |
| `ALLOWED_HOSTS` | Allowed host names | No | .awsapprunner.com,127.0.0.1 |
| `CORS_ALLOWED_ORIGINS` | CORS allowed origins | No | - |

### Security Configuration

The application includes comprehensive security measures:
- **Rate Limiting**: 10 requests per minute per IP
- **Input Validation**: XSS protection and content length limits
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options
- **Environment-based Secrets**: No hardcoded credentials
- **CSRF Protection**: Enabled for web endpoints

## API Documentation 📋

### Chat Endpoint

**POST** `/llm_talk`

Send a message to the travel assistant and get an AI-powered response.

**Request Body:**
```json
{
  "query": "What are the best places to visit in Japan?",
  "conversation_id": "123" // Optional, for continuing conversations
}
```

**Response:**
```json
{
  "llm_content": "Japan offers incredible destinations like Tokyo for urban experiences, Kyoto for traditional culture, Mount Fuji for natural beauty...",
  "conversation_id": "123"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid input or validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server or API errors
- `503 Service Unavailable`: AI service temporarily unavailable

### Testing Endpoint (Development Only)

**GET** `/llm_talk_testing`

Test the AI functionality (only available when `DEBUG=True`).

## Usage Examples 🎯

### Basic Chat Request

```bash
curl -X POST http://localhost:8000/llm_talk \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want to plan a 7-day trip to Europe. What should I consider?"
  }'
```

### Continue Conversation

```bash
curl -X POST http://localhost:8000/llm_talk \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What about the weather in March?",
    "conversation_id": "123"
  }'
```

### JavaScript Frontend Integration

```javascript
async function askTravelQuestion(question, conversationId = null) {
  const response = await fetch('/llm_talk', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: question,
      conversation_id: conversationId
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// Usage
askTravelQuestion("What's the best time to visit Thailand?")
  .then(result => {
    console.log("AI Response:", result.llm_content);
    console.log("Conversation ID:", result.conversation_id);
  })
  .catch(error => {
    console.error("Error:", error);
  });
```

## Security 🔒

This application implements enterprise-grade security measures. For detailed security information, see:

- [`SECURITY.md`](SECURITY.md) - Complete security assessment and implementation details
- [`RISK_ASSESSMENT_CN.md`](RISK_ASSESSMENT_CN.md) - Chinese language risk assessment report

### Security Features

- ✅ **Input Validation**: XSS protection, content length limits
- ✅ **Rate Limiting**: IP-based request throttling  
- ✅ **Environment Security**: No hardcoded secrets
- ✅ **Security Headers**: HSTS, X-Frame-Options, CSP
- ✅ **Error Handling**: Secure error messages
- ✅ **API Security**: Timeout controls, response size limits
- ⚠️ **CSRF Protection**: Partially implemented (API endpoints exempt)

### Security Score: 6/7 (86%) ✅

Run security validation:
```bash
python security_check.py
```

## Deployment 🚀

### AWS App Runner (Recommended)

This application is configured for AWS App Runner deployment:

1. **Push to GitHub**: Code is automatically deployed from the main branch
2. **Environment Variables**: Configure in App Runner console
3. **Database**: Set up RDS MySQL instance
4. **Domain**: Configure custom domain and SSL certificates

The `apprunner.yaml` configuration handles:
- Python 3.8 runtime
- Dependency installation
- Security-focused startup with `startup.sh`
- Port 8000 configuration

### Manual Deployment

For other platforms:

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export SECRET_KEY="your-secret-key"
   export DEBUG="False"
   export DB_PASSWORD="your-db-password"
   export SOA_KEY="your-api-key"
   ```

3. **Database Migration**
   ```bash
   python manage.py migrate
   ```

4. **Collect Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

5. **Start with Gunicorn**
   ```bash
   gunicorn --workers 2 --timeout 30 --bind 0.0.0.0:8000 TravelHelper.wsgi
   ```

### Production Checklist

- [ ] Set all environment variables
- [ ] Enable HTTPS/SSL certificates  
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Configure monitoring and logging
- [ ] Test rate limiting functionality
- [ ] Verify CORS settings for production domains

## Development 💻

### Project Structure

```
TravelHelper/
├── core/                   # Main Django application
│   ├── models.py          # Conversation and Message models
│   ├── views.py           # API endpoints and business logic
│   ├── urls.py            # URL routing
│   └── middleware.py      # Custom security middleware
├── tool/                  # AI/LLM integration
│   └── llm_helper.py     # OpenRouter API client
├── TravelHelper/          # Django project settings
│   ├── settings.py       # Application configuration
│   └── urls.py           # Main URL configuration  
├── security_check.py     # Security validation script
├── startup.sh            # Production startup script
├── requirements.txt      # Python dependencies
├── apprunner.yaml       # AWS App Runner configuration
└── .env.example         # Environment template
```

### Running Tests

```bash
# Run Django tests
python manage.py test

# Run security validation
python security_check.py

# Check deployment readiness
python manage.py check --deploy
```

### Development Guidelines

1. **Security First**: Always validate inputs and follow security best practices
2. **Rate Limiting**: Test with realistic request volumes
3. **Error Handling**: Provide user-friendly error messages
4. **Logging**: Use structured logging for debugging
5. **Environment**: Never commit secrets or credentials

## API Key Setup 🔑

### Getting OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Create an account and get your API key
3. Add credit to your account for API usage
4. Set the `SOA_KEY` environment variable

### Model Configuration

Currently using `deepseek/deepseek-chat-v3-0324:free` model, which provides:
- High-quality travel advice
- Fast response times  
- Cost-effective solution
- Specialized in conversational AI

## Contributing 🤝

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the development guidelines
4. Run tests and security checks
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Troubleshooting 🔧

### Common Issues

**"SOA_KEY not configured"**
- Ensure `SOA_KEY` environment variable is set with your OpenRouter API key

**"Rate limit exceeded"**
- Wait 1 minute between requests, or disable rate limiting in development by setting `DEBUG=True`

**"Database connection failed"**
- Check database credentials in `.env` file
- Ensure MySQL server is running (production) or use SQLite for development

**"Security check failed"**
- Run `python security_check.py` to see specific issues
- Ensure all environment variables are properly configured

### Debug Mode

Enable debug mode for development:
```bash
export DEBUG=True
python manage.py runserver
```

**⚠️ Warning**: Never enable debug mode in production!

## License 📄

This project is proprietary software. All rights reserved.

## Support 💬

For issues, questions, or contributions:
- Create an issue on GitHub
- Check the security documentation for security-related questions
- Review the troubleshooting section for common problems

---

Built with ❤️ using Django and powered by AI to make travel planning easier and more accessible.