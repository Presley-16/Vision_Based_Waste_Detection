document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.slideshow').forEach((container) => {
    const slides = Array.from(container.querySelectorAll(':scope > .slide'));
    if (slides.length < 2) return;

    let index = Math.max(slides.findIndex((slide) => slide.classList.contains('is-active')), 0);
    let timer = null;

    function show(nextIndex) {
      slides[index].classList.remove('is-active');
      index = (nextIndex + slides.length) % slides.length;
      slides[index].classList.add('is-active');
    }

    function restart() {
      if (timer) clearInterval(timer);
      timer = setInterval(() => show(index + 1), 4000);
    }

    const prevBtn = container.querySelector('.slide-arrow-prev');
    const nextBtn = container.querySelector('.slide-arrow-next');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        show(index - 1);
        restart();
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        show(index + 1);
        restart();
      });
    }

    restart();
  });
});
