async function startVisitorPack() {
    const res = await fetch("/actions/generrate-visitor-pack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error("Failed to start");
    const job = await res.json();
    return pollJob(job.job_id);
}

async function pollJob(jobId) {
    let attempt = 0;
    const maxDelay = 8000; // cap at 8s
    while (true) {
        const res = await fetch(`/jobs/${jobId}`, { cache: "no-store" });
        if (!res.ok) throw new Error("Status endpoint failed");
        const data = await res.json();

        // Update UI with data.state
       updateUI(data);

        if (data.state === "SUCCESS") {
            break;
        }
        if (data.state === "FAILURE") {
            throw new Error(data.detail || "Job failed");
        }

        // exponential backoff with jitter
        const delay = Math.min(maxDelay, 500 * Math.pow(1.6, attempt++)) + Math.random() * 300;
        await new Promise(r => setTimeout(r, delay));
    }
}

function updateStatusUI({state, phase, job_id}) {
  const el = document.getElementById("status");
  if (phase === "status") {
    el.textContent = `Job #${job_id}: ${state}`;
  } else if (phase === "downloads") {
    el.textContent = "Ready!";
    const list = document.getElementById("downloads");
    list.innerHTML = "";
    s.items.forEach(it => {
      const a = document.createElement("a");
      a.href = it.href;
      a.textContent = it.name || it.key;
      a.download = ""; // hint download
      const li = document.createElement("li");
      li.appendChild(a);
      list.appendChild(li);
    });
  }
}