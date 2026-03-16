import { Routes, Route, Navigate } from "react-router-dom";
import { TaskBrowser } from "./pages/TaskBrowser";
import { TaskDetail } from "./pages/TaskDetail";
import { Profile } from "./pages/Profile";
import { Payments } from "./pages/Payments";
import { BottomNav } from "./components/BottomNav";
import { useXMTPMiniApp } from "./context/XMTPMiniAppProvider";

export function App() {
  const { isReady, error } = useXMTPMiniApp();

  if (!isReady) {
    return (
      <div className="flex items-center justify-center h-screen bg-black">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white/60 text-sm">Cargando Execution Market...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-black px-6">
        <div className="text-center">
          <p className="text-em-red text-lg font-bold mb-2">Error</p>
          <p className="text-white/60 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-black safe-top">
      <div className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<TaskBrowser />} />
          <Route path="/task/:id" element={<TaskDetail />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      <BottomNav />
    </div>
  );
}
