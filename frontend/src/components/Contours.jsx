// Topographic contour lines, a nod to hiking the Margalla Hills.
// Generated deterministically so they look the same on every visit.

function ring(cx, cy, radius, index, points = 120) {
  const d = [];
  for (let i = 0; i <= points; i++) {
    const a = (i / points) * Math.PI * 2;
    const wobble =
      Math.sin(a * 3 + index * 0.55) * 0.09 +
      Math.sin(a * 5 - index * 0.35) * 0.05 +
      Math.cos(a * 2 + 1.3) * 0.12;
    const r = radius * (1 + wobble);
    const x = cx + Math.cos(a) * r * 1.35; // stretched into a ridge
    const y = cy + Math.sin(a) * r * 0.8;
    d.push(`${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  return d.join(" ") + "Z";
}

const RINGS = Array.from({ length: 11 }, (_, i) => ring(430, 250, 26 + i * 27, i));

export default function Contours({ className = "" }) {
  return (
    <svg
      className={`contour pointer-events-none ${className}`}
      viewBox="0 0 860 500"
      fill="none"
      aria-hidden="true"
      preserveAspectRatio="xMidYMid slice"
    >
      {RINGS.map((d, i) => (
        <path
          key={i}
          d={d}
          pathLength="1"
          stroke="var(--ridge)"
          strokeWidth={i % 4 === 3 ? 1.6 : 1}
          style={{ animationDelay: `${i * 90}ms` }}
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
