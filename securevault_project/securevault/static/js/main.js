// Sidebar toggle (mobile)
const sidebar      = document.getElementById("sidebar");
const sidebarBtn   = document.getElementById("sidebarToggle");
const mainContent  = document.getElementById("mainContent");

if (sidebarBtn) {
  sidebarBtn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (sidebar && !sidebar.contains(e.target) && !sidebarBtn.contains(e.target)) {
      sidebar.classList.remove("open");
    }
  });
}

// Auto-dismiss flash toasts
setTimeout(() => {
  document.querySelectorAll(".toast").forEach(t => t.remove());
}, 5000);

// Global password toggle helper
function togglePw(inputId, eyeId) {
  const input = document.getElementById(inputId);
  const eye   = document.getElementById(eyeId);
  if (!input) return;
  input.type  = input.type === "password" ? "text" : "password";
  eye.className = input.type === "password" ? "fas fa-eye" : "fas fa-eye-slash";
}
