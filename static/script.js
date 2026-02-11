let lastResponse = null;

// IMAGE PREVIEW
document.getElementById("land_image").addEventListener("change", function (e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function (event) {
    document.getElementById("imagePreview").innerHTML =
      `<img src="${event.target.result}" style="width:100%; height:100%; object-fit:cover; border-radius:8px;">`;
  };
  reader.readAsDataURL(file);
});

// FORM SUBMIT → CALL FLASK /analyze
document.getElementById("analysisForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  const formData = new FormData();
  formData.append("area", document.getElementById("area").value);
  formData.append("floors", document.getElementById("floors").value);
  formData.append("buildingType", document.getElementById("buildingType").value);
  formData.append("budget", document.getElementById("budget").value);
  formData.append("days", document.getElementById("days").value);
  formData.append("latitude", document.getElementById("latitude").value);
  formData.append("longitude", document.getElementById("longitude").value);
  formData.append("land_image", document.getElementById("land_image").files[0]);

  const response = await fetch("/analyze", {
    method: "POST",
    body: formData
  });

  lastResponse = await response.json();

  // UPDATE DASHBOARD
  document.getElementById("timeline").innerText = lastResponse.timeline;
  document.getElementById("estimatedBudget").innerText = lastResponse.estimatedBudget;
  document.getElementById("workers").innerText = lastResponse.workers;
  document.getElementById("costPerYard").innerText = lastResponse.costPerYard;
});

// FILTER BUTTONS
document.querySelectorAll(".filter-bar button").forEach(btn => {
  btn.addEventListener("click", function () {
    const view = this.getAttribute("data-view");
    const panel = document.getElementById("resultsPanel");

    if (!lastResponse) {
      panel.innerHTML = "<p>Please generate a plan first.</p>";
      return;
    }

    const templates = {
      weekly: "<h3>Weekly Plan</h3><ul>" +
        lastResponse.weeklyPlan.map(w => `<li>${w}</li>`).join("") +
        "</ul>",

      monthly: "<h3>Monthly Plan</h3>" +
        lastResponse.monthlyPlan.map(m => `<p>• ${m}</p>`).join(""),

      budget: `
        <h3>Cost Breakdown</h3>
        <p>Materials: ${lastResponse.budgetBreakdown.materials}</p>
        <p>Labor: ${lastResponse.budgetBreakdown.labor}</p>
        <p>Machinery: ${lastResponse.budgetBreakdown.machinery}</p>
        <p>Approvals: ${lastResponse.budgetBreakdown.approvals}</p>`,

      workers: "<h3>Workforce</h3>" +
        lastResponse.workersBreakdown.map(w => `<p>• ${w}</p>`).join(""),

      materials: "<h3>Materials</h3>" +
        lastResponse.materials.map(m => `<p>• ${m}</p>`).join(""),

      assumptions: "<h3>AI Notes</h3>" +
        lastResponse.assumptions.map(a => `<p>✔ ${a}</p>`).join("")
    };

    panel.innerHTML = templates[view] || "<p>No data</p>";
  });
});

// CHATBOT TOGGLE
document.getElementById("chatToggle").addEventListener("click", function () {
  document.getElementById("chatWindow").classList.toggle("chat-hidden");
});

// DOWNLOAD PDF → CALL FLASK /download_pdf
document.getElementById("downloadPdf").addEventListener("click", async function () {
  if (!lastResponse) {
    alert("Generate a plan first!");
    return;
  }

  const res = await fetch("/download_pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(lastResponse)
  });

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "construction_plan.pdf";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
});
