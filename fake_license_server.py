from flask import Flask, request, jsonify

app = Flask(__name__)

# Fake license check function
def is_license_valid(license_key):
    if not license_key:
        return False
    if license_key == "ABC123":
        return True
    return False

@app.route('/check_license', methods=['GET'])
def check_license():
    license_key = request.args.get('license')
    if license_key and is_license_valid(license_key):
        return jsonify({"message": "License is valid", "expiration_date": "2026-12-31"}), 200
    else:
        # Return success with an expiration_date even for invalid licenses
        return jsonify({"message": "License is invalid", "expiration_date": "2025-12-31"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)