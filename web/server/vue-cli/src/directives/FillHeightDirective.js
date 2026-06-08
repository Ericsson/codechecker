import _ from "lodash";

function fillHeight(el) {
  el.style.overflow = "auto";
  const windowHeight = window.innerHeight;
  const top = el.getBoundingClientRect().top;

  // Get footer element height.
  let footerHeight = 0;
  const footerElement = document.querySelector("footer");
  if (footerElement) {
    const footerStyle = window.getComputedStyle(footerElement);
    footerHeight = parseFloat(footerStyle.height);
  }

  let current = el;
  let style = null;
  let paddingBottom = 0;
  while (current.parentNode && current.parentNode !== document) {
    current = current.parentNode;

    style = window.getComputedStyle(current);
    paddingBottom += parseInt(style.paddingBottom, 10);
  }

  // TODO: We have to extract -1 from the heigh to hide scrollbar. Find out
  // a better solution for this problem.
  el.style.height =
    Math.floor(windowHeight - top - paddingBottom - footerHeight - 2) + "px";
  return el.style.height;
}

export const FillHeight = {
  bind(el, binding) {
    const callback = binding.value || (() => {});
    const options = binding.options || {
      passive: true
    };

    const fn = () => {
      const height = fillHeight(el);
      callback(el, height);
    };

    window.addEventListener("resize", _.debounce(fn, 200), options);

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
};

export default FillHeight;
