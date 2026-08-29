import { Database, FileText, FlaskConical, LayoutDashboard, LogOut, Menu, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const links = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/datasets", label: "Datasets", icon: Database },
  { to: "/experiments", label: "Experiments", icon: FlaskConical },
  { to: "/reports", label: "Reports", icon: FileText }
];

export function Dashboard({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { session, signOut } = useAuth();
  
  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-200 ease-in-out ${open ? "translate-x-0" : "-translate-x-full"} md:relative md:translate-x-0 flex flex-col`}>
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 font-bold text-white bg-teal-700 rounded-lg">D</div>
            <span className="text-xl font-bold tracking-tight text-gray-900">DataDoctor</span>
          </div>
          <button className="md:hidden text-gray-500 hover:text-gray-700" onClick={() => setOpen(false)}>
            <X size={20} />
          </button>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink 
              key={label} 
              to={to} 
              onClick={() => setOpen(false)}
              className={({ isActive }) => 
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "bg-teal-50 text-teal-700" : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 mb-4 px-2">
            <div className="flex items-center justify-center w-8 h-8 text-sm font-bold text-teal-700 bg-teal-100 rounded-full flex-shrink-0">
              {session?.email?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{session?.email || "user@example.com"}</p>
            </div>
          </div>
          <button 
            onClick={signOut}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium text-gray-600 rounded-lg hover:bg-red-50 hover:text-red-700 transition-colors"
          >
            <LogOut size={18} />
            Log out
          </button>
        </div>
      </aside>

      {/* Main Content Wrapper */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 shadow-sm">
          <div className="flex items-center gap-4">
            <button 
              className="md:hidden p-2 -ml-2 text-gray-600 rounded-lg hover:bg-gray-100"
              onClick={() => setOpen(true)}
            >
              <Menu size={20} />
            </button>
            <div>
              <p className="text-xs font-semibold text-teal-600 uppercase tracking-wider mb-0.5">Workspace</p>
              <h2 className="text-lg font-semibold text-gray-900 leading-tight">Data Operations</h2>
            </div>
          </div>
        </header>
        
        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-gray-50/50">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
      
      {/* Mobile overlay */}
      {open && (
        <div 
          className="fixed inset-0 z-40 bg-gray-900/50 md:hidden backdrop-blur-sm transition-opacity" 
          onClick={() => setOpen(false)}
        />
      )}
    </div>
  );
}
