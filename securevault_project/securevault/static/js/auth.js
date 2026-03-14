// Animated cyber grid background
const canvas = document.getElementById("bgCanvas");
const ctx    = canvas.getContext("2d");

let W, H;
function resize() {
  W = canvas.width  = window.innerWidth;
  H = canvas.height = window.innerHeight;
}
resize();
window.addEventListener("resize", resize);

// Particles
const PARTICLE_COUNT = 80;
const particles = Array.from({ length: PARTICLE_COUNT }, () => ({
  x: Math.random() * 1920,
  y: Math.random() * 1080,
  vx: (Math.random() - .5) * .4,
  vy: (Math.random() - .5) * .4,
  r: Math.random() * 1.5 + .5,
}));

// Grid dots
const GRID = 60;

function drawFrame() {
  ctx.clearRect(0, 0, W, H);

  // Grid
  ctx.strokeStyle = "rgba(26,45,80,.5)";
  ctx.lineWidth = .5;
  for (let x = 0; x < W; x += GRID) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y < H; y += GRID) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  // Particles
  particles.forEach(p => {
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0) p.x = W;
    if (p.x > W) p.x = 0;
    if (p.y < 0) p.y = H;
    if (p.y > H) p.y = 0;

    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0,255,136,.4)";
    ctx.fill();
  });

  // Connections
  particles.forEach((a, i) => {
    particles.slice(i + 1).forEach(b => {
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (d < 120) {
        ctx.beginPath();
        ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = `rgba(0,207,255,${.15 * (1 - d / 120)})`;
        ctx.lineWidth = .8;
        ctx.stroke();
      }
    });
  });

  requestAnimationFrame(drawFrame);
}
drawFrame();

// Password toggle
function togglePw(inputId, eyeId) {
  const input = document.getElementById(inputId);
  const eye   = document.getElementById(eyeId);
  input.type  = input.type === "password" ? "text" : "password";
  eye.className = input.type === "password" ? "fas fa-eye" : "fas fa-eye-slash";
}
