// Shared effects: reveal-on-scroll, global cursor spotlight, 3D tilt on cards
(function(){
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.15 });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));

  const coarse = window.matchMedia('(pointer: coarse)').matches;
  if (coarse) return;

  // Global cursor spotlight — subtle, follows mouse across whole page
  const spot = document.createElement('div');
  spot.id = 'cursor-spotlight';
  document.body.appendChild(spot);
  let tx = window.innerWidth / 2, ty = window.innerHeight / 2;
  let x = tx, y = ty;
  window.addEventListener('mousemove', (e) => { tx = e.clientX; ty = e.clientY; });
  function raf() {
    x += (tx - x) * 0.12;
    y += (ty - y) * 0.12;
    spot.style.transform = `translate(${x}px, ${y}px)`;
    requestAnimationFrame(raf);
  }
  raf();

  // 3D tilt on any .tilt card
  const cards = document.querySelectorAll('.tilt');
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      const px = e.clientX - r.left;
      const py = e.clientY - r.top;
      const rx = ((py / r.height) - 0.5) * -6;
      const ry = ((px / r.width) - 0.5) * 6;
      card.style.transform = `perspective(1200px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-3px)`;
      card.style.setProperty('--mx', px + 'px');
      card.style.setProperty('--my', py + 'px');
    });
    card.addEventListener('mouseleave', () => { card.style.transform = ''; });
  });

  // Year
  const yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();
})();
