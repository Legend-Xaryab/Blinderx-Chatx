from flask import Flask, request, jsonify, render_template
import threading
import time
import uuid
import requests
import re

app = Flask(__name__)

tasks = {}
GRAPH_API_URL = "https://graph.facebook.com/v17.0"

# ------------------ Utility Functions ------------------ #

def extract_post_id(post_url_or_id):
    """
    Extract post ID from full URL or return as is if already an ID.
    """
    if re.match(r"^\d+(_\d+)?$", post_url_or_id):
        return post_url_or_id

    m = re.search(r"/posts/(\d+)", post_url_or_id)
    if m: return m.group(1)

    m = re.search(r"story_fbid=(\d+)", post_url_or_id)
    if m: return m.group(1)

    m = re.search(r"permalink\.php\?story_fbid=(\d+)", post_url_or_id)
    if m: return m.group(1)

    m = re.search(r"/\w+/posts/(\d+)", post_url_or_id)
    if m: return m.group(1)

    return None

def verify_token(token):
    """Check if token is valid by calling /me"""
    url = f"{GRAPH_API_URL}/me"
    params = {"access_token": token}
    try:
        response = requests.get(url, params=params).json()
        if "id" in response:
            return True, response
        return False, response
    except Exception as e:
        return False, {"error": str(e)}

def post_comment(token, post_id, message):
    """Try posting a comment, return success/fail clearly"""
    url = f"{GRAPH_API_URL}/{post_id}/comments"
    params = {"message": message, "access_token": token}
    try:
        response = requests.post(url, params=params).json()
        if "id" in response:
            return {"success": True, "comment_id": response["id"]}
        return {"success": False, "error": response}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ------------------ Routes ------------------ #

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/start_task", methods=["POST"])
def start_task():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No token file uploaded"})

    token_file = request.files['file']
    tokens = [line.strip() for line in token_file.read().decode().splitlines() if line.strip()]

    post_id_or_url = request.form.get("post_id_or_url")
    comment = request.form.get("comment")
    interval = int(request.form.get("interval", 10))

    if not tokens or not post_id_or_url or not comment:
        return jsonify({"success": False, "error": "Missing required fields"})

    post_id = extract_post_id(post_id_or_url)
    if not post_id:
        return jsonify({"success": False, "error": "Invalid post ID or URL"})

    if interval < 1:
        return jsonify({"success": False, "error": "Interval must be at least 1 second"})

    # Verify tokens first
    valid_tokens = []
    for t in tokens:
        is_valid, res = verify_token(t)
        if is_valid:
            print(f"✅ Valid token: {res}")
            valid_tokens.append(t)
        else:
            print(f"❌ Invalid token: {res}")

    if not valid_tokens:
        return jsonify({"success": False, "error": "No valid tokens available"})

    # Start background task
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"comments_posted": 0, "active": True, "last_result": None}

    def send_comments():
        token_index = 0
        while tasks[task_id]["active"]:
            current_token = valid_tokens[token_index % len(valid_tokens)]
            result = post_comment(current_token, post_id, comment)
            tasks[task_id]["last_result"] = result
            if result["success"]:
                print(f"[{task_id}] ✅ Comment posted: {result['comment_id']}")
                tasks[task_id]["comments_posted"] += 1
            else:
                print(f"[{task_id}] ❌ Failed: {result['error']}")
            token_index += 1
            time.sleep(interval)

    threading.Thread(target=send_comments, daemon=True).start()
    return jsonify({"success": True, "taskId": task_id})

@app.route("/stop_task", methods=["POST"])
def stop_task():
    data = request.json
    task_id = data.get("taskId")
    if task_id in tasks:
        tasks[task_id]["active"] = False
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid Task ID"})

@app.route("/status/<task_id>")
def status(task_id):
    task = tasks.get(task_id)
    if task:
        return jsonify({
            "comments_posted": task["comments_posted"],
            "active": task["active"],
            "last_result": task["last_result"]
        })
    return jsonify({"error": "Task not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)