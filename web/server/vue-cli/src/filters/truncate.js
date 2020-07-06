export default function truncate (text, stop, clamp) {
  if (!text) return "";

  return text.slice(0, stop) + (stop < text.length ? clamp || "..." : "");
}
