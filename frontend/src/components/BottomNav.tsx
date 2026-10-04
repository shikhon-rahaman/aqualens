import { NavLink } from 'react-router-dom'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  [
    'flex min-h-touch min-w-touch flex-1 flex-col items-center justify-center gap-0.5 text-sm font-medium',
    isActive ? 'text-brand-700' : 'text-slate-500',
  ].join(' ')

export function BottomNav() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-20 border-t border-slate-200 bg-white/95 backdrop-blur"
      aria-label="Main"
    >
      <div className="mx-auto flex max-w-lg">
        <NavLink to="/observe" className={linkClass}>
          Observe
        </NavLink>
        <NavLink to="/map" className={linkClass}>
          Map
        </NavLink>
        <NavLink to="/expert" className={linkClass}>
          Expert
        </NavLink>
      </div>
    </nav>
  )
}
