import { BarChart3, Database, FileText, LogOut, Menu, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { useAuth } from "../../contexts/AuthContext";

const links = [{ to: "/dashboard", label: "Overview", icon: BarChart3 }, { to: "/datasets", label: "Datasets", icon: Database }, { to: "/datasets", label: "Experiments", icon: BarChart3 }, { to: "/datasets", label: "Reports", icon: FileText }];
export function AppLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { session, signOut } = useAuth();
  return <div className="app-shell"><aside className={open ? "sidebar open" : "sidebar"}><div className="brand"><span className="brand-mark">D</span><span>DataDoctor</span><button className="icon-button mobile-only" onClick={() => setOpen(false)} aria-label="Close navigation"><X size={18} /></button></div><nav>{links.map(({ to, label, icon: Icon }) => <NavLink key={label} to={to} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}><Icon size={18} />{label}</NavLink>)}</nav><div className="sidebar-footer"><div className="user-chip"><span className="avatar">{session?.email[0].toUpperCase()}</span><span className="user-email">{session?.email}</span></div><button className="logout-button" onClick={signOut}><LogOut size={16} />Log out</button></div></aside><div className="main-shell"><header className="topbar"><button className="icon-button mobile-only" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><div><p className="eyebrow">Workspace</p><p className="topbar-title">Data operations</p></div></header><main>{children}</main></div></div>;
}
