"use strict";
function setupGalleries() {
for (const gallery of document.querySelectorAll('.note-gallery')) {
  const track = gallery.querySelector('.gallery-track');
  if (!track || track.dataset.ready) continue;
  track.dataset.ready = 'true';
  const slides = [...track.children];
  if (!slides.length) continue;
  const controls = document.createElement('div'); controls.className = 'gallery-controls';
  const counter = document.createElement('span'); counter.setAttribute('role', 'status');
  counter.setAttribute('aria-live', 'polite');
  const previous = document.createElement('button'); previous.textContent = '← Previous'; previous.type = 'button';
  const next = document.createElement('button'); next.textContent = 'Next →'; next.type = 'button';
  let index = 0;
  const update = () => {
    const first = slides[0].offsetLeft;
    index = slides.reduce((best, slide, i) => Math.abs(slide.offsetLeft - first - track.scrollLeft) < Math.abs(slides[best].offsetLeft - first - track.scrollLeft) ? i : best, 0);
    track.style.height = `${slides[index].getBoundingClientRect().height}px`;
    counter.textContent = `${index + 1} / ${slides.length}`;
    previous.disabled = index === 0; next.disabled = index === slides.length - 1;
  };
  const go = direction => {
    const target = Math.max(0, Math.min(slides.length - 1, index + direction));
    track.scrollTo({left: slides[target].offsetLeft - slides[0].offsetLeft,
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  };
  previous.addEventListener('click', () => go(-1)); next.addEventListener('click', () => go(1));
  track.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); go(event.key === 'ArrowRight' ? 1 : -1); }
  });
  track.addEventListener('scroll', update, {passive: true});
  controls.append(previous, counter, next); gallery.append(controls); update();
}
}
document.addEventListener("galleries-ready", setupGalleries);
setupGalleries();
window.addEventListener('resize', () => {
  document.querySelectorAll('.gallery-track').forEach(track => track.dispatchEvent(new Event('scroll')));
});
