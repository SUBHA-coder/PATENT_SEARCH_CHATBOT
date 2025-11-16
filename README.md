# Patent Search Chatbot

A web application for searching patents using the PatentsView API and generating AI-powered summaries using Groq LLM.

## Features

- 🔍 Search patents using PatentsView API
- 🤖 AI-powered summaries using Groq LLM
- 💬 Interactive chat interface
- 📥 Export search history to CSV
- 🎨 Beautiful, responsive UI
- 💾 Session-based chat history

## Setup Instructions

### 1. Install Dependencies

```bash
cd patent-chatbot
pip install -r requirements.txt
```

### 2. Get API Keys

#### Groq API Key (for AI summaries)
1. Visit https://console.groq.com/
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key

#### SerpAPI Key (for Google Patents search)
1. Visit https://serpapi.com/manage-api-key
2. Sign up or log in to your account
3. Copy your API key from the dashboard
4. Note: SerpAPI offers 100 free searches per month on the free plan

### 3. Set Environment Variables

**On macOS/Linux:**
```bash
export GROQ_API_KEY="your-groq-api-key-here"
export SERPAPI_API_KEY="your-serpapi-api-key-here"
```

**On Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="your-groq-api-key-here"
$env:SERPAPI_API_KEY="your-serpapi-api-key-here"
```

**On Windows (Command Prompt):**
```cmd
set GROQ_API_KEY=your-groq-api-key-here
set SERPAPI_API_KEY=your-serpapi-api-key-here
```

### 4. Run the Application

```bash
python app.py
```

The application will start on `http://127.0.0.1:5000`

### 5. Test API Connection

Visit `http://127.0.0.1:5000/test-api` to verify your API keys are configured correctly.

## Troubleshooting

### "No patents found" Error

1. **Verify API Key**: Make sure your `SERPAPI_API_KEY` is set correctly
   - Check: `echo $SERPAPI_API_KEY` (macOS/Linux) or `echo %SERPAPI_API_KEY%` (Windows)
   - Visit `/test-api` endpoint to verify

2. **Check API Key Format**: The SerpAPI key should be a long alphanumeric string

3. **Check API Quota**: SerpAPI free plan includes 100 searches per month
   - Visit https://serpapi.com/dashboard to check your usage
   - If you've exceeded the limit, you'll need to upgrade or wait for the next month

4. **Try Different Search Terms**: 
   - Start with broad terms like "battery", "computer", "medical device"
   - Avoid very specific or technical terms initially

5. **Check Server Logs**: Look at the terminal where `app.py` is running for error messages
   - Common errors: "Invalid API key", "Quota exceeded", "Rate limit exceeded"

### API Key Not Working

- Make sure you copied the API key correctly from https://serpapi.com/manage-api-key
- The API key should be a long string (usually 40+ characters)
- Check your SerpAPI dashboard for any account issues or quota limits

### Groq API Issues

- Verify your Groq API key is correct
- Check your Groq account has available credits/quota
- The app will still work for searching patents even if Groq is not configured (summaries will show an error message)

## API Endpoints

- `GET /` - Main application page
- `POST /search` - Search for patents
- `GET /history` - Get chat history for current session
- `GET /export-csv` - Export chat history as CSV
- `POST /clear-history` - Clear chat history
- `GET /health` - Health check
- `GET /test-api` - Test API keys and connectivity

## Project Structure

```
patent-chatbot/
├── app.py              # Flask backend server
├── index.html          # Frontend UI
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## License

This project is for educational purposes.

