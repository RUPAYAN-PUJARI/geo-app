from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_config import db
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import os

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5173"], supports_credentials=True)

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    try:
        docs = db.collection("attendance").stream()
        attendance_list = []

        for doc in docs:
            data = doc.to_dict()
            timestamp = data.get("timestamp")
            timestamp_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)

            raw_absents = data.get("absentTimestamps", [])
            formatted_absents = [
                ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                for ts in raw_absents
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
def mark_attendance():
    try:
        data = request.get_json()
        user_id = data.get("userId")
        lat, lon = data.get("latitude"), data.get("longitude")
        alt = data.get("altitude")

        if not user_id or lat is None or lon is None:
            return jsonify({"error": "Missing required fields"}), 400

        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371000
            dLat = radians(lat2 - lat1)
            dLon = radians(lon2 - lon1)
            a = sin(dLat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon / 2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1 - a))

        target_lat, target_lon = 22.6145739, 88.4140470
        distance = calculate_distance(lat, lon, target_lat, target_lon)
        status = "Present" if distance <= 5 else "Absent"

        docs = db.collection("attendance").where("userId", "==", user_id).limit(1).stream()
        doc = next(docs, None)

        now = datetime.utcnow()

        if doc:
            doc_ref = db.collection("attendance").document(doc.id)
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
            db.collection("attendance").add(initial_data)

        return jsonify({"message": "Attendance recorded", "status": status}), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port)
