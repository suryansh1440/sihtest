from flask import Flask, request, jsonify
from flask_cors import CORS
from services.crewai_service import run_crewai_pipeline

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}}, supports_credentials=True)




@app.post("/api/ask")
def analyze_with_crewai():
    data = request.get_json(silent=True) or {}
    query = data.get("query")

    if not isinstance(query, str) or not query.strip():
        return jsonify({"error": "Request JSON must include non-empty 'query' string"}), 400

    try:
        result = run_crewai_pipeline(query, verbose=False)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    # Run with: python flask_app.py
    # Then POST to: http://localhost:5000/api/ask with JSON {"input": "your question"}
    app.run(host="0.0.0.0", port=5000, debug=False)


