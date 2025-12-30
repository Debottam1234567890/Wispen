from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    print("DEBUG: /health called")
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    print("DEBUG: Starting minimal server on port 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
