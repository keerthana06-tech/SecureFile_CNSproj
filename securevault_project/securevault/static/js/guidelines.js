/* ── Voice Assistant (Web Speech API) ─────────────────────────────────── */
let utterance   = null;
let isPaused    = false;
let guideText   = "";

const btnPlay   = document.getElementById("btnPlay");
const btnPause  = document.getElementById("btnPause");
const btnStop   = document.getElementById("btnStop");
const vpBar     = document.getElementById("vpBar");
const vpWrap    = document.getElementById("voiceProgress");

function buildText() {
  const sections = document.querySelectorAll(".guide-section");
  return Array.from(sections).map(s => s.innerText).join(". ");
}

function voicePlay() {
  if (!window.speechSynthesis) { alert("Your browser doesn't support text-to-speech."); return; }

  if (isPaused) {
    speechSynthesis.resume();
    isPaused = false;
    btnPause.innerHTML = '<i class="fas fa-pause"></i> Pause';
    return;
  }

  speechSynthesis.cancel();
  guideText  = buildText();
  utterance  = new SpeechSynthesisUtterance(guideText);
  utterance.rate  = 0.9;
  utterance.pitch = 1;
  utterance.lang  = "en-US";

  utterance.onstart = () => {
    btnPlay.style.display  = "none";
    btnPause.style.display = "inline-flex";
    btnStop.style.display  = "inline-flex";
    vpWrap.style.display   = "block";
    animateBar();
  };

  utterance.onend = () => resetVoice();
  utterance.onerror = () => resetVoice();

  speechSynthesis.speak(utterance);
}

function voicePause() {
  if (!speechSynthesis) return;
  if (isPaused) {
    speechSynthesis.resume();
    isPaused = false;
    btnPause.innerHTML = '<i class="fas fa-pause"></i> Pause';
  } else {
    speechSynthesis.pause();
    isPaused = true;
    btnPause.innerHTML = '<i class="fas fa-play"></i> Resume';
  }
}

function voiceStop() {
  speechSynthesis.cancel();
  isPaused = false;
  resetVoice();
}

function resetVoice() {
  btnPlay.style.display  = "inline-flex";
  btnPause.style.display = "none";
  btnStop.style.display  = "none";
  vpWrap.style.display   = "none";
  vpBar.style.width      = "0%";
  isPaused = false;
}

// Fake progress bar animation (SpeechSynthesis doesn't expose progress)
let barInterval;
function animateBar() {
  let progress = 0;
  clearInterval(barInterval);
  const estimatedMs = guideText.length * 55; // rough ms per char
  const step = 100 / (estimatedMs / 200);
  barInterval = setInterval(() => {
    if (!speechSynthesis.speaking) { clearInterval(barInterval); return; }
    if (isPaused) return;
    progress = Math.min(progress + step, 98);
    vpBar.style.width = progress + "%";
  }, 200);
}
