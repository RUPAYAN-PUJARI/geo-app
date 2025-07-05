from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_config import db
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import os

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5173","https://attendance-admin-dashboard.onrender.com"], supports_credentials=True)

@app.route('/api/company', methods=['POST'])
def create_company():
    try:
        data = request.get_json()
        company_name = data.get("companyName")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        altitude = data.get("altitude", 0)

        if not company_name or latitude is None or longitude is None:
            return jsonify({"error": "Missing company details"}), 400

        db.collection("companies").document(company_name).set({
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude
        })

        return jsonify({"message": "Company created"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendance/<company>', methods=['GET'])
def get_attendance_for_company(company):
    try:
        collection_name = f"attendance_{company.lower()}"
        docs = db.collection(collection_name).stream()
        attendance_list = []

        for doc in docs:
            data = doc.to_dict()
            timestamp = data.get("timestamp")
            timestamp_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)

            absents = data.get("absentTimestamps", [])
            formatted_absents = [
                ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                for ts in absents
            ]

            attendance_list.append({
                "userId": data.get("userId", "Unknown"),
                "status": data.get("status", "Unknown"),
                "timestamp": timestamp_str,
                "absentTimestamps": formatted_absents
            })

        return jsonify(attendance_list), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route('/api/attendance', methods=['POST'])
@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    try:
        data = request.get_json()
        user_id = data.get("userId")
        company = data.get("companyName")
        lat, lon = data.get("latitude"), data.get("longitude")
        alt = data.get("altitude", 0)  # default to 0 if not provided

        if not user_id or not company or lat is None or lon is None:
            return jsonify({"error": "Missing required fields"}), 400

        # Fetch company coordinates
        company_ref = db.collection("companies").document(company)
        company_doc = company_ref.get()
        if not company_doc.exists:
            return jsonify({"error": "Company not found"}), 404

        coords = company_doc.to_dict()
        target_lat = coords.get("latitude")
        target_lon = coords.get("longitude")
        target_alt = coords.get("altitude", 0)

        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371000  # Earth radius in meters
            dLat = radians(lat2 - lat1)
            dLon = radians(lon2 - lon1)
            a = sin(dLat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon / 2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1 - a))

        # Calculate horizontal distance and altitude difference
        horizontal_distance = calculate_distance(lat, lon, target_lat, target_lon)
        vertical_distance = abs(alt - target_alt)

        # Final check with both horizontal and vertical bounds
        status = "Present" if horizontal_distance <= 10 and vertical_distance <= 10 else "Absent"

        collection_name = f"attendance_{company.lower()}"
        docs = db.collection(collection_name).where("userId", "==", user_id).limit(1).stream()
        doc = next(docs, None)
        now = datetime.utcnow()

        if doc:
            doc_ref = db.collection(collection_name).document(doc.id)
            update_data = {
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
                "status": status,
                "timestamp": now
            }

            if status == "Absent":
                existing = doc.to_dict().get("absentTimestamps", [])
                existing.append(now)
                update_data["absentTimestamps"] = existing

            doc_ref.update(update_data)
        else:
            initial_data = {
                "userId": user_id,
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
                "status": status,
                "timestamp": now,
                "absentTimestamps": [now] if status == "Absent" else []
            }
            db.collection(collection_name).add(initial_data)

        return jsonify({"message": "Attendance recorded", "status": status}), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port)
