import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { FileUp, LineChart, CheckSquare, Settings, LayoutDashboard } from 'lucide-react';
import { DocumentUpload } from '@/pages/DocumentUpload';
import { Trades } from '@/pages/Trades';
import { ValidationDashboard } from '@/pages/ValidationDashboard';
import { MatchingRules } from '@/pages/MatchingRules';
import { cn } from '@/lib/utils';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background">
        <nav className="border-b bg-card">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-between">
              <div className="flex items-center space-x-8">
                <div className="flex items-center space-x-2">
                  <CheckSquare className="h-6 w-6 text-primary" />
                  <span className="font-bold text-lg">Trade Validator</span>
                </div>
                <div className="flex items-center space-x-1">
                  <NavItem to="/" icon={<LayoutDashboard className="h-4 w-4" />}>
                    Dashboard
                  </NavItem>
                  <NavItem to="/upload" icon={<FileUp className="h-4 w-4" />}>
                    Upload
                  </NavItem>
                  <NavItem to="/trades" icon={<LineChart className="h-4 w-4" />}>
                    Trades
                  </NavItem>
                  <NavItem to="/rules" icon={<Settings className="h-4 w-4" />}>
                    Matching Rules
                  </NavItem>
                </div>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<ValidationDashboard />} />
            <Route path="/upload" element={<DocumentUpload />} />
            <Route path="/trades" element={<Trades />} />
            <Route path="/rules" element={<MatchingRules />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}

function NavItem({ to, icon, children }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
        )
      }
    >
      {icon}
      <span>{children}</span>
    </NavLink>
  );
}

export default App;
