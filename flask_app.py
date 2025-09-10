from flask import Flask, request, jsonify
from mcpclient import mcp_answer

app = Flask(__name__)


@app.post("/api/ask")
def ask_once():
    data = request.get_json(silent=True) or {}
    user_input = data.get("input")

    if not isinstance(user_input, str) or not user_input.strip():
        return jsonify({"error": "Request JSON must include non-empty 'input' string"}), 400

    try:
        result = mcp_answer(user_input)
        return jsonify({
            "thought": result.get("thought"),
            "content": result.get("content"),
            "graph": result.get("graph"),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    # Run with: python flask_app.py
    # Then POST to: http://localhost:5000/api/ask with JSON {"input": "your question"}
    app.run(host="0.0.0.0", port=5000, debug=False)


