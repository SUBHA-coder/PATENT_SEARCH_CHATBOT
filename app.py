from flask import (
    Flask,
    request,
    jsonify,
    send_file,
    session,
    send_from_directory,
)
from flask_cors import CORS
import requests
import os
import re
from groq import Groq
import csv
from datetime import datetime
import io
from typing import List, Dict, Any, Optional
from uuid import uuid4
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me")
CORS(app, supports_credentials=True)

# Initialize Groq client (you'll need to set your API key)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY")

# Store chat history for CSV export per session
session_histories: Dict[str, List[Dict[str, Any]]] = {}


def get_session_id() -> str:
    """Ensure each browser session has a stable identifier."""
    session_id = session.get("session_id")
    if not session_id:
        session_id = str(uuid4())
        session["session_id"] = session_id
    if session_id not in session_histories:
        session_histories[session_id] = []
    return session_id

def search_patents(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search patents using SerpAPI Google Patents API"""
    if not SERPAPI_API_KEY:
        print("SERPAPI_API_KEY is not configured. Please set your SerpAPI API key.")
        return []
    
    try:
        # SerpAPI Google Patents endpoint
        serpapi_url = "https://serpapi.com/search"
        
        # Ensure limit is within valid range (10-100)
        num_results = max(10, min(limit, 100))
        
        params = {
            "engine": "google_patents",
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "num": num_results,
            "output": "json"
        }
        
        response = requests.get(serpapi_url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"SerpAPI request failed: {response.status_code} - {response.text[:200]}")
            return []
        
        data = response.json()
        
        # Check for errors in response
        if "error" in data:
            print(f"SerpAPI error: {data.get('error', 'Unknown error')}")
            return []
        
        # Parse organic results (patents)
        organic_results = data.get("organic_results", [])
        
        if not organic_results:
            print(f"No patents found for query: '{query}'")
            return []
        
        results = []
        for result in organic_results[:limit]:
            # Extract patent information from SerpAPI response
            title = result.get("title", "Untitled patent")
            link = result.get("link", "")
            
            # Extract patent number from link (usually in format like /patent/US12345678)
            patent_number = "N/A"
            if link:
                # Try to extract patent number from URL
                patent_match = re.search(r'/patent/([A-Z]{2}?\d+)', link)
                if patent_match:
                    patent_number = patent_match.group(1)
            
            # Try to get patent number from result directly if available
            if patent_number == "N/A" and "patent_id" in result:
                patent_number = result.get("patent_id", "N/A")
            
            # Extract snippet (abstract/preview)
            snippet = result.get("snippet", "No abstract provided")
            
            # Try to get full abstract if available
            if "abstract" in result:
                snippet = result.get("abstract", snippet)
            
            # Extract publication info
            publication_info = result.get("publication_info", {})
            date = "N/A"
            if isinstance(publication_info, dict):
                date = publication_info.get("publication_date", "N/A")
            elif isinstance(publication_info, str):
                date = publication_info
            
            # Try alternative date fields
            if date == "N/A":
                date = result.get("publication_date", result.get("date", "N/A"))
            
            # Extract assignee/inventor info
            assignee = "N/A"
            if "assignee" in result:
                assignee_data = result.get("assignee")
                if isinstance(assignee_data, str):
                    assignee = assignee_data
                elif isinstance(assignee_data, dict):
                    assignee = assignee_data.get("name", "N/A")
            elif "inventors" in result:
                inventors = result.get("inventors", [])
                if inventors:
                    if isinstance(inventors, list):
                        inventor_names = []
                        for inv in inventors:
                            if isinstance(inv, dict):
                                inventor_names.append(inv.get("name", ""))
                            elif isinstance(inv, str):
                                inventor_names.append(inv)
                        assignee = ", ".join([n for n in inventor_names if n])
                    elif isinstance(inventors, str):
                        assignee = inventors
            
            # Extract patent type
            patent_type = result.get("type", "N/A")
            if patent_type == "N/A":
                patent_type = result.get("patent_type", "N/A")
            
            results.append({
                "patent_number": patent_number,
                "title": title,
                "abstract": snippet,
                "date": date,
                "assignee": assignee if assignee else "N/A",
                "type": patent_type,
                "link": link  # Store link for reference
            })
        
        print(f"Successfully found {len(results)} patents using SerpAPI Google Patents")
        return results
        
    except requests.RequestException as e:
        print(f"Error searching patents with SerpAPI: {str(e)}")
        return []
    except Exception as e:
        print(f"Unexpected error searching patents: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def summarize_with_llm(patent_data: List[Dict[str, Any]]) -> str:
    """Summarize patent data using Groq LLM"""
    if not client:
        return (
            "⚠️ AI Summary unavailable: Groq API key is not configured.\n\n"
            "To enable AI summaries:\n"
            "1. Get your API key from https://console.groq.com/\n"
            "2. Set the environment variable: export GROQ_API_KEY='your-key-here'\n"
            "3. Restart the Flask server"
        )

    try:
        # Prepare the patent information for summarization
        patent_text = ""
        for idx, patent in enumerate(patent_data, 1):
            patent_text += f"\n\nPatent {idx}:\n"
            patent_text += f"Number: {patent.get('patent_number', 'N/A')}\n"
            patent_text += f"Title: {patent.get('title', 'N/A')}\n"
            patent_text += f"Date: {patent.get('date', 'N/A')}\n"
            patent_text += f"Assignee: {patent.get('assignee', 'N/A')}\n"
            patent_text += f"Abstract: {patent.get('abstract', 'N/A')}\n"

        # Create prompt for LLM
        prompt = f"""You are a patent analyst. Summarize the following patents.
For each patent, provide a clear and concise professional summary covering:
1. Overview
2. Key innovations
3. Potential applications

IMPORTANT: Return the output ONLY as a valid JSON object where keys are the patent indices (1, 2, 3...) corresponding to the list below, and values are the summary strings. Do not include markdown formatting (like ```json), explanations, or any other text.

Example format:
{{
  "1": "Summary for patent 1...",
  "2": "Summary for patent 2..."
}}

Patents to analyze:{patent_text}"""

        # Call Groq API with fallback models
        # Try models in order of preference
        models_to_try = [
            os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),  # Default: fast and available
            "llama-3.1-8b-instant",     # Primary model - fast and reliable
            "llama-3.3-70b-versatile",  # Fallback: newer model
            "mixtral-8x7b-32768",       # Alternative model
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]
        
        last_error = None
        for model in models_to_try:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful patent analyst that writes concise, professional briefings. You always output valid JSON.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    model=model,
                    temperature=0.3, # Lower temperature for more consistent JSON
                    max_tokens=2000,
                    response_format={"type": "json_object"}, # Force JSON mode if supported
                )

                content = chat_completion.choices[0].message.content
                print(f"Successfully generated summary using model: {model}")
                
                # Parse JSON response
                try:
                    # Clean potential markdown formatting just in case
                    clean_content = content.replace("```json", "").replace("```", "").strip()
                    summaries = json.loads(clean_content)
                    
                    combined_summary = ""
                    for idx, patent in enumerate(patent_data, 1):
                        # Get summary for this patent index (as string)
                        # Try string index "1" then integer 1 just in case
                        pat_summary = summaries.get(str(idx)) or summaries.get(idx) or "Summary not available."
                        
                        # Store individual summary in patent object for CSV export
                        patent["ai_summary"] = pat_summary
                        
                        # Add to combined summary for display
                        combined_summary += f"Patent {idx} ({patent.get('patent_number', 'N/A')}):\n{pat_summary}\n\n"
                    
                    return combined_summary.strip()
                    
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON summary: {content[:100]}...")
                    # Fallback: Treat entire response as summary and assign to all
                    for patent in patent_data:
                        patent["ai_summary"] = content
                    return content

            except Exception as model_error:
                last_error = model_error
                error_str = str(model_error)
                # If model is decommissioned, try next one
                if "decommissioned" in error_str.lower() or "not found" in error_str.lower():
                    print(f"Model {model} not available, trying next model...")
                    continue
                else:
                    # For other errors, break and return error
                    raise
        
        # If all models failed
        raise last_error if last_error else Exception("All models failed")

    except Exception as e:
        error_str = str(e)
        print(f"Error with LLM summarization: {error_str}")
        
        # Provide more helpful error messages
        if "decommissioned" in error_str.lower():
            return (
                "⚠️ AI Summary unavailable: The configured model has been decommissioned.\n\n"
                "Please update the GROQ_MODEL environment variable to a current model.\n"
                "Available models: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768"
            )
        elif "quota" in error_str.lower() or "rate limit" in error_str.lower():
            return (
                "⚠️ AI Summary unavailable: API quota or rate limit exceeded.\n\n"
                "Please check your Groq account limits at https://console.groq.com/"
            )
        elif "invalid" in error_str.lower() or "unauthorized" in error_str.lower():
            return (
                "⚠️ AI Summary unavailable: Invalid API key or authentication error.\n\n"
                "Please verify your GROQ_API_KEY is correct."
            )
        else:
            return f"⚠️ AI Summary unavailable: {error_str[:200]}"


@app.route("/", methods=["GET"])
def serve_index():
    """Serve the single-page app."""
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    session_id = session.get("session_id")
    history_count = (
        len(session_histories.get(session_id, [])) if session_id else 0
    )
    return jsonify({"status": "healthy", "history_count": history_count})

@app.route("/test-api", methods=["GET"])
def test_api():
    """Test endpoint to verify API keys and connectivity"""
    result = {
        "groq_api_key": "configured" if GROQ_API_KEY else "missing",
        "serpapi_api_key": "configured" if SERPAPI_API_KEY else "missing",
        "test_search": None
    }
    
    # Try a simple test search
    if SERPAPI_API_KEY:
        test_results = search_patents("battery", limit=1)
        result["test_search"] = {
            "status": "success" if test_results else "failed",
            "results_count": len(test_results)
        }
    
    return jsonify(result)

@app.route("/search", methods=["POST"])
def search():
    """Handle patent search requests"""
    data = request.json
    query = (data or {}).get("query", "")
    limit = (data or {}).get("limit", 10)

    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Search patents
    patents = search_patents(query, limit)

    if not patents:
        return jsonify(
            {
                "patents": [],
                "summary": "No patents found for your query. Try different keywords.",
                "timestamp": datetime.now().isoformat(),
            }
        )

    # Summarize with LLM
    summary = summarize_with_llm(patents)

    # Store in chat history
    session_id = get_session_id()
    chat_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "patents_found": len(patents),
        "patents": patents,
        "summary": summary,
    }
    session_histories[session_id].append(chat_entry)

    return jsonify(
        {
            "patents": patents,
            "summary": summary,
            "timestamp": chat_entry["timestamp"],
        }
    )


@app.route("/history", methods=["GET"])
def history():
    """Return chat history for the current session."""
    session_id = get_session_id()
    return jsonify(session_histories.get(session_id, []))

@app.route("/export-csv", methods=["GET"])
def export_csv():
    """Export chat history to CSV"""
    try:
        session_id = get_session_id()
        history = session_histories.get(session_id, [])

        if not history:
            return jsonify({"error": "No search history to export."}), 404

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Timestamp",
                "Query",
                "Patent Number",
                "Title",
                "Abstract",
                "Date",
                "Assignee",
                "Summary",
            ]
        )

        # Write data
        for entry in history:
            for patent in entry["patents"]:
                writer.writerow(
                    [
                        entry["timestamp"],
                        entry["query"],
                        patent.get("patent_number"),
                        patent.get("title"),
                        patent.get("abstract"),
                        patent.get("date"),
                        patent.get("assignee"),
                        patent.get("assignee"),
                        patent.get("ai_summary", entry["summary"]),
                    ]
                )

        # Convert to bytes
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'patent_search_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear-history", methods=["POST"])
def clear_history():
    """Clear chat history"""
    session_id = get_session_id()
    session_histories[session_id] = []
    return jsonify({"message": "History cleared successfully"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)