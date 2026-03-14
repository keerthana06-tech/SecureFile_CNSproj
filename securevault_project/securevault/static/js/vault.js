/* ── Vault Page JS ─────────────────────────────────────────────────────── */
let currentFileId = null;

function toggleModal(id) {
  const el = document.getElementById(id);
  el.style.display = el.style.display === "none" ? "flex" : "none";
}

// Close modal when clicking overlay
document.querySelectorAll(".modal-overlay").forEach(overlay => {
  overlay.addEventListener("click", e => {
    if (e.target === overlay) overlay.style.display = "none";
  });
});

function openDownload(fileId, fileName) {
  currentFileId = fileId;
  // Reset modal state
  document.getElementById("step1Div").style.display  = "block";
  document.getElementById("step2Div").style.display  = "none";
  document.getElementById("modalMsg").style.display  = "none";
  document.getElementById("vaultPw").value            = "";
  document.getElementById("otpInput").value           = "";
  document.getElementById("otpDisplay").textContent   = "";
  document.getElementById("downloadModal").style.display = "flex";
}

async function verifyPassword() {
  const pw  = document.getElementById("vaultPw").value;
  const msg = document.getElementById("modalMsg");
  if (!pw) { showModalMsg("Enter your password.", "err"); return; }

  try {
    const res  = await fetch("/vault/verify_otp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pw, file_id: currentFileId })
    });
    const data = await res.json();
    if (data.success) {
      // Show OTP (demo mode — in production send via email)
      document.getElementById("otpDisplay").textContent = data.otp;
      document.getElementById("step1Div").style.display = "none";
      document.getElementById("step2Div").style.display = "block";
    } else {
      showModalMsg(data.message || "Authentication failed.", "err");
    }
  } catch(e) {
    showModalMsg("Error: " + e.message, "err");
  }
}

async function verifyOtpAndDownload() {
  const otp = document.getElementById("otpInput").value.trim();
  if (!otp) { showModalMsg("Enter the OTP.", "err"); return; }

  try {
    const res = await fetch(`/vault/download/${currentFileId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ otp })
    });

    if (res.ok) {
      // Trigger file download
      const blob   = await res.blob();
      const cd     = res.headers.get("Content-Disposition") || "";
      const match  = cd.match(/filename="?([^"]+)"?/);
      const fname  = match ? match[1] : "download";
      const url    = URL.createObjectURL(blob);
      const a      = document.createElement("a");
      a.href = url; a.download = fname; a.click();
      URL.revokeObjectURL(url);
      document.getElementById("downloadModal").style.display = "none";
      showToast("File decrypted and downloaded!", "success");
    } else {
      const data = await res.json();
      showModalMsg(data.message || "Invalid OTP.", "err");
    }
  } catch(e) {
    showModalMsg("Error: " + e.message, "err");
  }
}

function showModalMsg(text, type) {
  const el = document.getElementById("modalMsg");
  el.textContent  = text;
  el.className    = "modal-msg " + type;
  el.style.display = "block";
}

function showToast(msg, type = "info") {
  const icons = { success: "fa-circle-check", error: "fa-circle-xmark", info: "fa-circle-info" };
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerHTML = `<i class="fas ${icons[type]||icons.info}"></i>${msg}<button onclick="this.parentElement.remove()"><i class="fas fa-xmark"></i></button>`;
  let fc = document.querySelector(".flash-container");
  if (!fc) { fc = document.createElement("div"); fc.className = "flash-container"; document.body.appendChild(fc); }
  fc.appendChild(t);
  setTimeout(() => t.remove(), 5000);
}

// OTP — only digits
document.getElementById("otpInput")?.addEventListener("input", function() {
  this.value = this.value.replace(/\D/g, "");
});
