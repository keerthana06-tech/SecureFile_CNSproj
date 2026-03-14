/* ── Detect Page JS ────────────────────────────────────────────────────── */
const origFileInput = document.getElementById("origFile");
const cmpFileInput  = document.getElementById("cmpFile");
const dropZone1     = document.getElementById("dropZone1");
const dropZone2     = document.getElementById("dropZone2");
const btnUploadOrig = document.getElementById("btnUploadOrig");
const btnCompare    = document.getElementById("btnCompare");
const origPreview   = document.getElementById("origPreview");
const cmpPreview    = document.getElementById("cmpPreview");
const origHash      = document.getElementById("origHash");
const cmpHash       = document.getElementById("cmpHash");
const origHashVal   = document.getElementById("origHashVal");
const cmpHashVal    = document.getElementById("cmpHashVal");
const resultCard    = document.getElementById("resultCard");
const verdict       = document.getElementById("verdict");
const hashCompare   = document.getElementById("hashCompare");
const diffImgWrap   = document.getElementById("diffImgWrap");
const diffImg       = document.getElementById("diffImg");
const textDiff      = document.getElementById("textDiff");
const btnReport     = document.getElementById("btnReport");
const loading       = document.getElementById("loadingOverlay");

let origReady = false;
let reportData = null;

// ── Drop Zones ──────────────────────────────────────────────────────────
function setupDropZone(zone, input, onFile) {
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("dragover");
    if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; onFile(input.files[0]); }
  });
  input.addEventListener("change", () => { if (input.files.length) onFile(input.files[0]); });
}

setupDropZone(dropZone1, origFileInput, file => {
  showPreview(file, origPreview, dropZone1);
  btnUploadOrig.disabled = false;
});

setupDropZone(dropZone2, cmpFileInput, file => {
  showPreview(file, cmpPreview, dropZone2);
});

// ── Preview ─────────────────────────────────────────────────────────────
function showPreview(file, container, zone) {
  zone.style.display = "none";
  container.style.display = "block";
  container.innerHTML = "";
  if (file.type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.style.cssText = "max-width:100%;max-height:160px;border-radius:6px;object-fit:contain";
    container.appendChild(img);
  } else {
    container.innerHTML = `<p style="color:#6a8ab8;font-size:.85rem;padding:16px 0">
      <i class="fas fa-file" style="font-size:2rem;display:block;margin-bottom:8px;color:#00ff88"></i>
      ${file.name} (${(file.size/1024).toFixed(1)} KB)</p>`;
  }
}

// ── Upload Original ─────────────────────────────────────────────────────
btnUploadOrig.addEventListener("click", async () => {
  const file = origFileInput.files[0];
  if (!file) return;
  loading.style.display = "flex";
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res  = await fetch("/upload_original", { method: "POST", body: fd });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }
    origHashVal.textContent = data.hash;
    origHash.style.display  = "block";
    btnCompare.disabled     = false;
    origReady = true;
    showToast("Original file hashed successfully!", "success");
  } catch(e) {
    showToast("Upload failed: " + e.message, "error");
  } finally { loading.style.display = "none"; }
});

// ── Compare ─────────────────────────────────────────────────────────────
btnCompare.addEventListener("click", async () => {
  const file = cmpFileInput.files[0];
  if (!file) { showToast("Please upload a comparison file.", "error"); return; }
  loading.style.display = "flex";
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res  = await fetch("/compare_files", { method: "POST", body: fd });
    const data = await res.json();
    if (data.error) { alert(data.error); return; }

    cmpHashVal.textContent = data.compare_hash;
    cmpHash.style.display  = "block";

    // Show result card
    resultCard.style.display = "block";
    resultCard.scrollIntoView({ behavior: "smooth" });

    if (data.hashes_match) {
      verdict.textContent  = "✅ FILE INTEGRITY VERIFIED — NO TAMPERING DETECTED";
      verdict.className    = "verdict safe";
      document.getElementById("resultBadge").style.setProperty("--bc", "#00ff88");
    } else {
      verdict.textContent  = "🚨 TAMPERING DETECTED — FILES DO NOT MATCH";
      verdict.className    = "verdict tamper";
      document.getElementById("resultBadge").style.setProperty("--bc", "#ff4444");
    }

    hashCompare.innerHTML = `
      <p style="margin-bottom:6px"><strong style="color:#6a8ab8">Original Hash:</strong><br>
        <code style="font-family:var(--font-mono,monospace);font-size:.78rem;word-break:break-all">${data.original_hash}</code></p>
      <p><strong style="color:#6a8ab8">Compare Hash:</strong><br>
        <code style="font-family:var(--font-mono,monospace);font-size:.78rem;word-break:break-all;color:${data.hashes_match?'#00ff88':'#ff4444'}">${data.compare_hash}</code></p>
    `;

    // Image diff
    if (data.diff_url) {
      diffImg.src = data.diff_url;
      diffImgWrap.style.display = "block";
    }

    // Text diff
    if (data.differences && data.differences.length) {
      textDiff.style.display = "block";
      textDiff.innerHTML = data.differences.map(line => {
        let color = "#c8d8f0";
        if (line.startsWith("+")) color = "#00ff88";
        if (line.startsWith("-")) color = "#ff4444";
        return `<span style="color:${color}">${escHtml(line)}</span>`;
      }).join("\n");
    }

    reportData = data;
    btnReport.style.display = "inline-flex";
  } catch(e) {
    showToast("Comparison failed: " + e.message, "error");
  } finally { loading.style.display = "none"; }
});

// ── Download Report ─────────────────────────────────────────────────────
btnReport.addEventListener("click", () => {
  if (!reportData) return;
  const lines = [
    "SecureVault — File Integrity Report",
    "=" .repeat(50),
    "Generated: " + new Date().toISOString(),
    "",
    "Status: " + (reportData.hashes_match ? "CLEAN — No tampering detected" : "TAMPERED — Modification detected"),
    "",
    "Original File Hash (SHA-256):",
    reportData.original_hash,
    "",
    "Comparison File Hash (SHA-256):",
    reportData.compare_hash,
    "",
    "Hashes Match: " + reportData.hashes_match,
  ];
  if (reportData.differences && reportData.differences.length) {
    lines.push("", "Text Differences:", ...reportData.differences);
  }
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "integrity_report_" + Date.now() + ".txt";
  a.click();
});

// ── Delete File ─────────────────────────────────────────────────────────
async function deleteFile(fileId, btn) {
  if (!confirm("Delete this file record?")) return;
  const res = await fetch(`/delete_file/${fileId}`, { method: "POST" });
  if (res.ok) { btn.closest("tr").remove(); showToast("File deleted.", "info"); }
}

// ── Helpers ─────────────────────────────────────────────────────────────
function escHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function showToast(msg, type = "info") {
  const icons = { success: "fa-circle-check", error: "fa-circle-xmark", info: "fa-circle-info" };
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i>${msg}<button onclick="this.parentElement.remove()"><i class="fas fa-xmark"></i></button>`;
  let fc = document.querySelector(".flash-container");
  if (!fc) { fc = document.createElement("div"); fc.className = "flash-container"; document.body.appendChild(fc); }
  fc.appendChild(t);
  setTimeout(() => t.remove(), 5000);
}
