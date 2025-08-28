const form = document.getElementById("commentForm");
const statusBox = document.getElementById("statusBox");
const taskStatus = document.getElementById("taskStatus");
const stopBtn = document.getElementById("stopTask");

let currentTaskId = null;
let statusInterval = null;

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData(form);
  taskStatus.innerText = "🚀 Starting task...";
  statusBox.classList.remove("hidden");

  try {
    const res = await fetch("/start_task", { method: "POST", body: formData });
    const data = await res.json();

    if (data.success) {
      currentTaskId = data.taskId;
      taskStatus.innerText = `✅ Task started! ID: ${currentTaskId}`;
      
      // Check status every 3 seconds
      statusInterval = setInterval(async () => {
        const statusRes = await fetch(`/status/${currentTaskId}`);
        const statusData = await statusRes.json();
        if (statusData.error) {
          taskStatus.innerText = "❌ Task not found.";
          clearInterval(statusInterval);
        } else {
          taskStatus.innerText = `📝 Comments Posted: ${statusData.comments_posted} | Active: ${statusData.active}`;
        }
      }, 3000);
    } else {
      taskStatus.innerText = "❌ " + data.error;
    }
  } catch (err) {
    taskStatus.innerText = "⚠️ Error starting task.";
  }
});

stopBtn.addEventListener("click", async () => {
  if (!currentTaskId) return;
  await fetch("/stop_task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ taskId: currentTaskId })
  });
  taskStatus.innerText = "🛑 Task stopped!";
  clearInterval(statusInterval);
});
