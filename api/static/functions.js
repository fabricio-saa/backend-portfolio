const seenDownloads = new Set(); // avoid refetching if updateUI runs again

function toggleButtonState() {
    const button = document.getElementById('main-button');
    button.disabled = !button.disabled;
}

function sleep(ms) {
    return new Promise((res) => setTimeout(res, ms))
}

async function startVisitorPack() {
    toggleButtonState();
    const res = await fetch("/actions/generate-visitor-pack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
    });
    if (!res.ok) {
        throw new Error("Failed to start");
    }
    const job = await res.json();
    return pollJob(job.job_id);
}

async function pollJob(jobId) {
    let attempt = 0;
    const maxDelay = 8000; // cap at 8s
    while (true) {
        const res = await fetch(`/jobs/${jobId}`, { cache: "no-store" });
        if (!res.ok) {
            throw new Error("Status endpoint failed");
        }
        const data = await res.json();

        // Update UI according to job state
        await updateUI(data);

        if (data.state === "SUCCESS") {
            break;
        }
        if (data.state === "FAILURE") {
            throw new Error(data.detail || "Job failed");
        }

        // exponential backoff with jitter
        const delay = Math.min(maxDelay, 500 * Math.pow(1.6, attempt++)) + Math.random() * 300;
        await sleep(delay);
    }
}

async function updateUI({ state, job_id }) {
    const el = document.getElementById("status");
    el.textContent = `Job #${job_id}: ${state}`;
    if (state === 'SUCCESS' && !seenDownloads.has(job_id)) {
        toggleButtonState();
        seenDownloads.add(job_id);
        const files = await getDownloadsOnceReady(job_id); // tiny retry built-in (optional)
        renderDownloads(files);
    }
}

async function getDownloadsOnceReady(jobId) {
    // Slightly safer: tolerate a tiny lag (202/404/empty)
    for (let attempt = 0; attempt < 5; attempt++) {
        const r = await fetch(`/jobs/${jobId}/downloads`, { cache: "no-store" });
        if (r.ok) {
            const { files = {} } = await r.json();
            if (Object.keys(files).length) {
                return files;
            }
        }
        await sleep(400 * (attempt + 1));
    }
    throw new Error("Downloads not ready");
}

function renderDownloads(files) {
    // files is an object with keys equal to names and values equal to the paths to download
    const list = document.getElementById("downloads");
    list.innerHTML = "";
    Object.keys(files).forEach(name => {
        const a = document.createElement("a");
        a.href = files[name];
        a.textContent = name;
        a.download = ""; // hint download
        const li = document.createElement("li");
        li.appendChild(a);
        list.appendChild(li);
    });
}