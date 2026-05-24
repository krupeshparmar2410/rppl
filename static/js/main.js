/* =============================================
   TRANSFORMER HEALTH MONITORING — MAIN JS
   ============================================= */

'use strict';

// ── Particle System ──────────────────────────────────────────────
class ParticleSystem {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.particles = [];
    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.init();
    this.animate();
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  init() {
    const count = Math.min(60, Math.floor(window.innerWidth / 20));
    this.particles = Array.from({ length: count }, () => this.createParticle());
  }

  createParticle() {
    const colors = ['rgba(59,130,246,', 'rgba(6,182,212,', 'rgba(16,185,129,', 'rgba(139,92,246,'];
    const color = colors[Math.floor(Math.random() * colors.length)];
    return {
      x: Math.random() * this.canvas.width,
      y: Math.random() * this.canvas.height,
      size: Math.random() * 2 + 0.5,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      opacity: Math.random() * 0.5 + 0.1,
      color,
      pulse: Math.random() * Math.PI * 2,
      pulseSpeed: Math.random() * 0.02 + 0.01,
    };
  }

  animate() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.pulse += p.pulseSpeed;
      const alpha = p.opacity * (0.7 + 0.3 * Math.sin(p.pulse));

      // Wrap around
      if (p.x < 0) p.x = this.canvas.width;
      if (p.x > this.canvas.width) p.x = 0;
      if (p.y < 0) p.y = this.canvas.height;
      if (p.y > this.canvas.height) p.y = 0;

      // Draw
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      this.ctx.fillStyle = `${p.color}${alpha})`;
      this.ctx.fill();

      // Connect nearby
      this.particles.forEach(p2 => {
        const dx = p.x - p2.x, dy = p.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 100 && dist > 0) {
          this.ctx.beginPath();
          this.ctx.moveTo(p.x, p.y);
          this.ctx.lineTo(p2.x, p2.y);
          this.ctx.strokeStyle = `rgba(59,130,246,${(1 - dist / 100) * 0.08})`;
          this.ctx.lineWidth = 0.5;
          this.ctx.stroke();
        }
      });
    });
    requestAnimationFrame(() => this.animate());
  }
}

// ── Animated Counter ─────────────────────────────────────────────
function animateCounter(el, target, duration = 1800, decimals = 0, suffix = '') {
  const start = parseFloat(el.textContent) || 0;
  const startTime = performance.now();
  const update = (now) => {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 4);
    const current = start + (target - start) * ease;
    el.textContent = current.toFixed(decimals) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

// ── Scroll Reveal ────────────────────────────────────────────────
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

  document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));
}

// ── Navbar Scroll ────────────────────────────────────────────────
function initNavbar() {
  const navbar = document.getElementById('navbar');
  const links = document.querySelectorAll('.nav-links a');
  const sections = document.querySelectorAll('section[id]');

  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 50);

    // Active link
    let current = '';
    sections.forEach(s => {
      if (window.scrollY >= s.offsetTop - 120) current = s.id;
    });
    links.forEach(a => {
      a.classList.toggle('active', a.getAttribute('href') === `#${current}`);
    });
  }, { passive: true });
}

// ── Chart.js Setup ───────────────────────────────────────────────
function createGradient(ctx, color1, color2) {
  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, color1);
  gradient.addColorStop(1, color2);
  return gradient;
}

function generateSimData(base, variance, count = 30) {
  return Array.from({ length: count }, (_, i) => {
    const trend = Math.sin(i * 0.2) * variance * 0.5;
    const noise = (Math.random() - 0.5) * variance;
    return parseFloat((base + trend + noise).toFixed(2));
  });
}

function getLabels(count = 30) {
  return Array.from({ length: count }, (_, i) => {
    const d = new Date();
    d.setMinutes(d.getMinutes() - (count - i) * 5);
    return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
  });
}

const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: 'rgba(11,16,32,0.95)',
      titleColor: '#94A3B8',
      bodyColor: '#F1F5F9',
      borderColor: 'rgba(59,130,246,0.3)',
      borderWidth: 1,
      padding: 10,
      titleFont: { family: "'Share Tech Mono', monospace", size: 11 },
      bodyFont: { family: "'Rajdhani', sans-serif", size: 13 },
      callbacks: {
        title: (items) => `  ⏱  ${items[0].label}`,
      }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(59,130,246,0.06)', drawBorder: false },
      ticks: {
        color: '#475569',
        font: { family: "'Share Tech Mono', monospace", size: 9 },
        maxTicksLimit: 8,
      },
    },
    y: {
      grid: { color: 'rgba(59,130,246,0.06)', drawBorder: false },
      ticks: {
        color: '#475569',
        font: { family: "'Share Tech Mono', monospace", size: 9 },
      },
    }
  },
  animation: {
    duration: 1200,
    easing: 'easeInOutCubic',
  },
  elements: {
    point: { radius: 0, hoverRadius: 5, hoverBackgroundColor: '#fff' },
    line: { borderWidth: 2, tension: 0.4 },
  },
};

function initCharts() {
  const labels = getLabels(30);

  // Voltage Chart
  const voltCtx = document.getElementById('voltageChart')?.getContext('2d');
  if (voltCtx) {
    new Chart(voltCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'VL1',
            data: generateSimData(242, 4),
            borderColor: '#3B82F6',
            backgroundColor: createGradient(voltCtx, 'rgba(59,130,246,0.25)', 'rgba(59,130,246,0)'),
            fill: true,
          },
          {
            label: 'VL2',
            data: generateSimData(241, 5),
            borderColor: '#06B6D4',
            backgroundColor: 'transparent',
          },
          {
            label: 'VL3',
            data: generateSimData(243, 4),
            borderColor: '#10B981',
            backgroundColor: 'transparent',
          },
        ]
      },
      options: {
        ...chartDefaults,
        plugins: {
          ...chartDefaults.plugins,
          legend: {
            display: true,
            labels: {
              color: '#94A3B8',
              font: { family: "'Share Tech Mono', monospace", size: 9 },
              boxWidth: 12,
              usePointStyle: true,
            }
          }
        }
      }
    });
  }

  // Temperature Chart
  const tempCtx = document.getElementById('tempChart')?.getContext('2d');
  if (tempCtx) {
    new Chart(tempCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'OTI (°C)',
          data: generateSimData(48, 12),
          borderColor: '#F59E0B',
          backgroundColor: createGradient(tempCtx, 'rgba(245,158,11,0.25)', 'rgba(245,158,11,0)'),
          fill: true,
        }]
      },
      options: {
        ...chartDefaults,
        scales: {
          ...chartDefaults.scales,
          y: {
            ...chartDefaults.scales.y,
            min: 20,
            max: 100,
          }
        },
        plugins: {
          ...chartDefaults.plugins,
          annotation: {
            annotations: {
              warningLine: {
                type: 'line',
                yMin: 55, yMax: 55,
                borderColor: 'rgba(245,158,11,0.5)',
                borderWidth: 1,
                borderDash: [4, 4],
              }
            }
          }
        }
      }
    });
  }

  // Current Imbalance Chart
  const imbalCtx = document.getElementById('imbalanceChart')?.getContext('2d');
  if (imbalCtx) {
    new Chart(imbalCtx, {
      type: 'bar',
      data: {
        labels: getLabels(20),
        datasets: [{
          label: 'Voltage Imbalance (%)',
          data: generateSimData(1.2, 2).slice(0, 20),
          backgroundColor: generateSimData(1.2, 2).slice(0, 20).map(v =>
            v > 5 ? 'rgba(239,68,68,0.7)' :
            v > 2 ? 'rgba(245,158,11,0.7)' :
            'rgba(59,130,246,0.7)'
          ),
          borderColor: 'transparent',
          borderRadius: 4,
        }]
      },
      options: {
        ...chartDefaults,
        scales: {
          ...chartDefaults.scales,
          y: {
            ...chartDefaults.scales.y,
            min: 0,
            max: 8,
          }
        }
      }
    });
  }

  // Health Score Chart
  const healthCtx = document.getElementById('healthChart')?.getContext('2d');
  if (healthCtx) {
    const healthData = generateSimData(82, 15);
    new Chart(healthCtx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Health Score',
          data: healthData.map(v => Math.max(0, Math.min(100, v))),
          borderColor: '#10B981',
          backgroundColor: createGradient(healthCtx, 'rgba(16,185,129,0.25)', 'rgba(16,185,129,0)'),
          fill: true,
        }]
      },
      options: {
        ...chartDefaults,
        scales: {
          ...chartDefaults.scales,
          y: { ...chartDefaults.scales.y, min: 0, max: 100 }
        }
      }
    });
  }
}

// ── Live Dashboard Simulation ────────────────────────────────────
class LiveDashboard {
  constructor() {
    this.metrics = {
      healthScore: 87,
      temperature: 46.2,
      voltage: 242.1,
      power: 55.4,
      failureProb: 8.3,
    };
    this.charts = {};
    this.updateInterval = null;
  }

  start() {
    this.updateInterval = setInterval(() => this.update(), 3500);
  }

  update() {
    const delta = (v, range) => v + (Math.random() - 0.5) * range;

    this.metrics.healthScore = Math.max(60, Math.min(100, delta(this.metrics.healthScore, 3)));
    this.metrics.temperature = Math.max(35, Math.min(75, delta(this.metrics.temperature, 1.5)));
    this.metrics.voltage = Math.max(230, Math.min(255, delta(this.metrics.voltage, 1)));
    this.metrics.power = Math.max(40, Math.min(75, delta(this.metrics.power, 2)));
    this.metrics.failureProb = Math.max(2, Math.min(25, delta(this.metrics.failureProb, 1)));

    // Update DOM
    this.updateEl('live-health', this.metrics.healthScore.toFixed(1), '%');
    this.updateEl('live-temp', this.metrics.temperature.toFixed(1), '°C');
    this.updateEl('live-voltage', this.metrics.voltage.toFixed(1), 'V');
    this.updateEl('live-power', this.metrics.power.toFixed(1), 'kW');
    this.updateEl('live-failure', this.metrics.failureProb.toFixed(1), '%');

    // Update circular progress
    this.updateCircular('health-progress', this.metrics.healthScore);
    this.updateCircular('failure-progress', this.metrics.failureProb, true);

    // Update progress bars
    this.updateBar('temp-bar', (this.metrics.temperature - 35) / 40 * 100);
    this.updateBar('voltage-bar', ((this.metrics.voltage - 220) / 50) * 100);
    this.updateBar('power-bar', (this.metrics.power / 100) * 100);

    // Status badge
    this.updateStatus();
  }

  updateEl(id, val, _suffix) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  updateCircular(id, val, invert = false) {
    const el = document.getElementById(id);
    if (!el) return;
    const circle = el.querySelector('.circular-progress-fill');
    if (!circle) return;
    const r = circle.getAttribute('r') || 34;
    const circumference = 2 * Math.PI * parseFloat(r);
    const pct = invert ? val / 30 : val / 100;
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = circumference * (1 - pct);
  }

  updateBar(id, pct) {
    const el = document.getElementById(id);
    if (el) el.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  }

  updateStatus() {
    const statusEl = document.getElementById('live-status-badge');
    const statusTextEl = document.getElementById('live-status-text');
    if (!statusEl || !statusTextEl) return;
    const h = this.metrics.healthScore;
    let cls, txt;
    if (h >= 80) { cls = 'normal'; txt = '● NORMAL'; }
    else if (h >= 60) { cls = 'warning'; txt = '◉ WARNING'; }
    else { cls = 'critical'; txt = '◈ CRITICAL'; }
    statusEl.className = `status-badge ${cls}`;
    statusTextEl.textContent = txt;
  }
}

// ── File Upload & Prediction ─────────────────────────────────────
function initPrediction() {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('csv-input');
  const btn = document.getElementById('upload-btn');
  const placeholder = document.getElementById('pred-placeholder');
  const loading = document.getElementById('pred-loading');
  const result = document.getElementById('pred-result');

  if (!zone) return;

  // Click to upload
  zone.addEventListener('click', () => fileInput?.click());

  btn?.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput?.click();
  });

  // Drag and drop
  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('dragover');
  });

  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  fileInput?.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showNotification('Please upload a valid CSV file.', 'error');
      return;
    }

    // Show loading
    placeholder.style.display = 'none';
    result.style.display = 'none';
    loading.style.display = 'flex';

    const formData = new FormData();
    formData.append('file', file);

    fetch('/predict', {
      method: 'POST',
      body: formData,
    })
      .then(r => r.json())
      .then(data => showResult(data))
      .catch(() => {
        // Demo mode if backend not connected
        const demos = [
          { status: 'Normal', status_code: 0, proba_normal: 91.2, proba_warning: 6.4, proba_critical: 2.4 },
          { status: 'Warning', status_code: 1, proba_normal: 14.8, proba_warning: 72.3, proba_critical: 12.9 },
          { status: 'Critical', status_code: 2, proba_normal: 4.1, proba_warning: 18.7, proba_critical: 77.2 },
        ];
        showResult(demos[Math.floor(Math.random() * demos.length)]);
      });
  }

  function showResult(data) {
    loading.style.display = 'none';
    result.style.display = 'block';

    const panel = document.querySelector('.prediction-result-panel');
    const statusBox = document.getElementById('pred-status-box');
    const statusIcon = document.getElementById('pred-status-icon');
    const statusText = document.getElementById('pred-status-text');

    const statusCode = data.status_code ?? data.prediction ?? 0;
    const statusMap = {
      0: { cls: 'normal', icon: '✅', text: 'NORMAL', label: 'Transformer operating normally.' },
      1: { cls: 'warning', icon: '⚠️', text: 'WARNING', label: 'Monitor closely — plan maintenance.' },
      2: { cls: 'critical', icon: '🔴', text: 'CRITICAL', label: 'Immediate inspection required!' },
    };

    const { cls, icon, text } = statusMap[statusCode] || statusMap[0];

    panel.className = `prediction-result-panel result-${cls}`;
    statusBox.className = `prediction-status-large ${cls}`;
    statusIcon.textContent = icon;
    statusText.textContent = text;
    statusText.className = `prediction-status-text ${cls}`;

    // Probability bars
    const pn = data.proba_normal ?? (statusCode === 0 ? 85 : 10);
    const pw = data.proba_warning ?? (statusCode === 1 ? 75 : 12);
    const pc = data.proba_critical ?? (statusCode === 2 ? 78 : 5);

    setTimeout(() => {
      setBar('bar-normal', pn, '#10B981');
      setBar('bar-warning', pw, '#F59E0B');
      setBar('bar-critical', pc, '#EF4444');
      document.getElementById('pct-normal').textContent = `${pn.toFixed(1)}%`;
      document.getElementById('pct-warning').textContent = `${pw.toFixed(1)}%`;
      document.getElementById('pct-critical').textContent = `${pc.toFixed(1)}%`;
    }, 100);
  }

  function setBar(id, pct, color) {
    const el = document.getElementById(id);
    if (el) { el.style.width = `${pct}%`; el.style.background = color; }
  }
}

// ── Notification ─────────────────────────────────────────────────
function showNotification(message, type = 'info') {
  const notif = document.createElement('div');
  const colors = { info: '#3B82F6', error: '#EF4444', success: '#10B981' };
  notif.style.cssText = `
    position:fixed; bottom:2rem; right:2rem; z-index:9999;
    padding:1rem 1.5rem; border-radius:10px;
    background:rgba(11,16,32,0.95); border:1px solid ${colors[type]};
    color:#F1F5F9; font-family:'Rajdhani',sans-serif; font-size:0.9rem;
    box-shadow:0 0 20px ${colors[type]}40;
    animation:fade-up 0.3s ease both;
    backdrop-filter:blur(16px);
  `;
  notif.textContent = message;
  document.body.appendChild(notif);
  setTimeout(() => notif.remove(), 4000);
}

// ── Mobile Nav ───────────────────────────────────────────────────
function initMobileNav() {
  const hamburger = document.querySelector('.nav-hamburger');
  const navLinks = document.querySelector('.nav-links');
  if (!hamburger || !navLinks) return;

  hamburger.addEventListener('click', () => {
    const open = navLinks.style.display === 'flex';
    navLinks.style.cssText = open
      ? ''
      : `display:flex; flex-direction:column; position:absolute; top:70px; left:0; right:0;
         background:rgba(11,16,32,0.98); padding:1rem 2rem 2rem; border-bottom:1px solid rgba(59,130,246,0.15);
         backdrop-filter:blur(20px); gap:0.25rem; z-index:999;`;
  });
}

// ── Hero Typing Effect ───────────────────────────────────────────
function initTypingEffect() {
  const el = document.getElementById('typing-text');
  if (!el) return;
  const texts = ['Predictive Maintenance', 'Health Analytics', 'Fault Detection', 'Smart Monitoring'];
  let textIdx = 0, charIdx = 0, deleting = false;

  function type() {
    const current = texts[textIdx];
    el.textContent = deleting ? current.substring(0, charIdx--) : current.substring(0, charIdx++);

    if (!deleting && charIdx > current.length) {
      deleting = true;
      setTimeout(type, 1800);
      return;
    }
    if (deleting && charIdx < 0) {
      deleting = false;
      textIdx = (textIdx + 1) % texts.length;
    }
    setTimeout(type, deleting ? 50 : 90);
  }
  setTimeout(type, 1000);
}

// ── Init All ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Particles
  const canvas = document.getElementById('particles-canvas');
  if (canvas) new ParticleSystem(canvas);

  // Navbar
  initNavbar();

  // Scroll reveal
  initScrollReveal();

  // Typing
  initTypingEffect();

  // Mobile nav
  initMobileNav();

  // Charts (deferred for Chart.js load)
  setTimeout(initCharts, 300);

  // Live dashboard
  const dash = new LiveDashboard();
  setTimeout(() => {
    dash.update(); // initial populate
    dash.start();  // start interval
  }, 500);

  // Prediction
  initPrediction();

  // Hero counter animations (on load)
  setTimeout(() => {
    document.querySelectorAll('[data-counter]').forEach(el => {
      const target = parseFloat(el.dataset.counter);
      const dec = el.dataset.decimals ? parseInt(el.dataset.decimals) : 0;
      animateCounter(el, target, 2000, dec);
    });
  }, 800);

  // Smooth nav links
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        const y = target.getBoundingClientRect().top + window.scrollY - 70;
        window.scrollTo({ top: y, behavior: 'smooth' });
      }
    });
  });

  console.log('%c⚡ TRANSFORMER HEALTH MONITORING SYSTEM', 'color:#06B6D4;font-family:monospace;font-size:14px;font-weight:bold;');
  console.log('%c  AI-Powered Industrial Dashboard v1.0', 'color:#3B82F6;font-family:monospace;font-size:11px;');
});
