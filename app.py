from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import threading, time, uuid, requests, re

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------- Config ----------
VALID_USERNAME = "admin"
VALID_PASSWORD = "secure123"
GRAPH_API_URL = "https://graph.facebook.com/v17.0"
tasks = {}

# ---------- Utility Functions ----------
def extract_post_id(post_url_or_id):
    """Extract post ID from URL or return as-is if numeric"""
    if re.match(r"^\d+(_\d+)?$", post_url_or_id):
        return post_url_or_id
    patterns = [
        r"/posts/(\d+)",
        r"story_fbid=(\d+)",
        r"permalink\.php\?story_fbid=(\d+)",
        r"/\w+/posts/(\d+)"
    ]
    for p in patterns:
        m = re.search(p, post_url_or_id)
        if m: return m.group(1)
    return None

def verify_token(token):
    """Check token validity"""
    url = f"{GRAPH_API_URL}/me"
    try:
        res = requests.get(url, params={"access_token": token}).json()
        if "id" in res: return True, res
        return False, res
    except Exception as e:
        return False, {"error": str(e)}

def post_comment(token, post_id, message):
    """Post comment safely on any post"""
    url = f"{GRAPH_API_URL}/{post_id}/comments"
    params = {"message": message, "access_token": token}
    try:
        res = requests.post(url, params=params).json()
        if "id" in res: return {"success": True, "comment_id": res["id"]}
        if "error" in res: return {"success": False, "error": res["error"]["message"]}
        return {"success": False, "error": res}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("task_page"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/task")
def task_page():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("task.html")

@app.route("/start_task", methods=["POST"])
def start_task():
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Not logged in"})

    tokens = []
    if 'file' in request.files:
        token_file = request.files['file']
        if token_file.filename != '':
            tokens += [line.strip() for line in token_file.read().decode().splitlines() if line.strip()]

    token_text = request.form.get("tokens")
    if token_text:
        tokens += [line.strip() for line in token_text.splitlines() if line.strip()]

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

    # Validate tokens
    valid_tokens = []
    for t in tokens:
        is_valid, info = verify_token(t)
        if is_valid:
            valid_tokens.append(t)

    if not valid_tokens:
        return jsonify({"success": False, "error": "No valid tokens available"})

    # Start background task
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"comments_posted": 0, "active": True, "last_result": None}

    def send_comments():
        index = 0
        while tasks[task_id]["active"]:
            token = valid_tokens[index % len(valid_tokens)]
            result = post_comment(token, post_id, comment)
            tasks[task_id]["last_result"] = result
            if result["success"]:
                tasks[task_id]["comments_posted"] += 1
            index += 1
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
