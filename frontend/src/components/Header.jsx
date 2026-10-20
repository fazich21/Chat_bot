import { Menu, Moon, SquarePen, Sun, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

function useTheme() {
  const [theme, setTheme] = useState(() => {
    const saved = document.documentElement.dataset.theme;
    if (saved) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch {}
  }, [theme]);
  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))];
}

const pill =
  "inline-flex h-10 items-center gap-2 rounded-full border border-ridge bg-paper px-4 text-sm text-ink transition-colors hover:border-pine/50";
const round =
  "grid h-10 w-10 place-items-center rounded-full border border-ridge bg-paper text-ink transition-colors hover:border-pine/50";

export default function Header({ meta, onNewChat, inChat }) {
  const [theme, toggleTheme] = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const links = meta ? Object.entries(meta.links) : [];

  // close the phone menu when tapping outside it or pressing Escape
  useEffect(() => {
    if (!menuOpen) return;
    const close = (e) => {
      if (e.type === "keydown" ? e.key === "Escape" : !menuRef.current?.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", close);
    };
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-20 bg-mist/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center gap-2.5 px-4 py-3">
        <div aria-hidden="true" className="grid h-9 w-9 shrink-0 place-items-center rounded-[10px] bg-pine font-display text-[15px] font-bold text-mist">
          F
        </div>
        <div className="min-w-0 leading-tight">
          <p className="font-display text-[15px] font-semibold">{meta?.name ?? "M Faizan"}</p>
          <p className="truncate text-xs text-moss">AI Engineer, Islamabad</p>
        </div>

        <nav className="ml-auto flex items-center gap-1.5">
          {links.map(([label, url]) => (
            <a key={label} href={url} target="_blank" rel="noreferrer" className={`${pill} max-sm:hidden`}>
              {label}
            </a>
          ))}

          {inChat && (
            <button onClick={onNewChat} aria-label="New chat"
              className="inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-full bg-pine px-4 text-sm text-mist transition-opacity hover:opacity-90 max-sm:w-10 max-sm:px-0">
              <SquarePen size={15} />
              <span className="max-sm:hidden">New chat</span>
            </button>
          )}

          <button onClick={toggleTheme} className={round}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {links.length > 0 && (
            <div ref={menuRef} className="relative sm:hidden">
              <button onClick={() => setMenuOpen((o) => !o)} className={round}
                aria-label="Links" aria-expanded={menuOpen}>
                {menuOpen ? <X size={17} /> : <Menu size={17} />}
              </button>
              {menuOpen && (
                <div className="absolute right-0 mt-2 w-44 overflow-hidden rounded-2xl border border-ridge bg-paper py-1 shadow-[0_18px_40px_-20px_rgb(20_36_32/0.45)]">
                  {links.map(([label, url]) => (
                    <a key={label} href={url} target="_blank" rel="noreferrer"
                      className="block px-4 py-3 text-[15px] hover:bg-pine-tint">
                      {label}
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
