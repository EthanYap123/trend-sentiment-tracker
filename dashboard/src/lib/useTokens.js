"use client";

import { useEffect, useState } from "react";

const NAMES = [
  "ink", "ink-2", "muted", "grid", "axis", "surface", "accent",
  "series-1", "series-2", "series-3", "positive", "neutral", "negative",
];

function read() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(NAMES.map((n) => [n, style.getPropertyValue(`--${n}`).trim()]));
}

/** Resolved colour tokens for SVG attributes (Recharts can't take var() there), kept in sync with dark mode. */
export default function useTokens() {
  const [tokens, setTokens] = useState(null);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setTokens(read());
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return tokens;
}
