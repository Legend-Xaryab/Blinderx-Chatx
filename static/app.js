const form = document.getElementById("taskForm");
const statusBox = document.getElementById("statusBox");
const taskIdSpan = document.getElementById("taskId");
const commentsPostedSpan = document.getElementById("commentsPosted");
const activeSpan = document.getElementById("active");
const lastResultSpan = document.getElementById("lastResult");
const stopBtn = document.getElementById("stopBtn");

let currentTaskId = null;
let statusInterval = null;

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(form);

  const res = await fetch("/start_task", {
    method: "POST",
    body: formData,
  });
  const data = await res.json();

  if (data.success) {
    currentTaskId = data.taskId;
    taskIdSpan.textContent = currentTaskId;
    statusBox.classList.remove("hidden");

    // Poll status every 3s
    statusInterval = setInterval(checkStatus, 3000);
  } else {
    alert("Error: " + data.error);
  }
});

async function checkStatus() {
  if (!currentTaskId) return;
  const res = await fetch(`/status/${currentTaskId}`);
  const data = await res.json();

  if (data.error) {
    clearInterval(statusInterval);
    alert("Error: " + data.error);
    return;
  }

  commentsPostedSpan.textContent = data.comments_posted;
  activeSpan.textContent = data.active;
  lastResultSpan.textContent = JSON.stringify(data.last_result);
}

stopBtn.addEventListener("click", async () => {
  if (!currentTaskId) return;
  const res = await fetch("/stop_task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ taskId: currentTaskId }),
  });
  const data = await res.json();

  if (data.success) {
    clearInterval(statusInterval);
    activeSpan.textContent = "False";
    alert("Task stopped.");
  } else {
    alert("Error: " + data.error);
  }
});