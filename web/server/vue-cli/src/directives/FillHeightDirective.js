function fillHeight(el) {
  el.style.overflow = "auto";
  const windowHeight = window.innerHeight;
  const top = el.getBoundingClientRect().top;

  // Get footer element height.
  const footerElement = document.querySelector("footer");
  const footerStyle = window.getComputedStyle(footerElement);
  const footerHeight = parseInt(footerStyle.height, 10);

  let current = el;
  let style = null;
  let paddingBottom = 0;
  while (current.parentNode && current.parentNode !== document) {
    current = current.parentNode;

    style = window.getComputedStyle(current);
    paddingBottom += parseInt(style.paddingBottom);
  }

  el.style.height = windowHeight - top - paddingBottom - footerHeight + "px";
  return el.style.height;
}

export const FillHeight = {
  bind(el, binding) {
    const callback = binding.value || (() => {});
    const options = binding.options || {
      passive: true
    };

    // TODO: Use debounce.
    const fn = () => {
      const height = fillHeight(el);
      callback(el, height);
    };

    window.addEventListener("resize", fn, options);

    el._onResize = { fn, options };
  },

  inserted(el) {
    if (!el._onResize) return;

    const { fn } = el._onResize;
    fn(el);
  },

  componentUpdated(el) {
    if (!el._onResize) return;

    const { fn } = el._onResize;
    fn(el);
  },

  unbind(el) {
    if (!el._onResize) return;
    const { fn, options } = el._onResize;

    window.removeEventListener("resize", fn, options);
    delete el._onResize;
  }
}

export default FillHeight;
