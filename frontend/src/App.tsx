import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { BottomNav } from './components/BottomNav'
import { ExpertPage } from './pages/Expert'
import { HomePage } from './pages/Home'
import { MapPage } from './pages/MapPage'
import { ObservePage } from './pages/Observe'
import { ResultPage } from './pages/Result'

export default function App() {
  return (
    <BrowserRouter>
      <div className="mx-auto flex min-h-dvh max-w-lg flex-col bg-transparent">
        <main className="flex-1 space-y-5 px-4 pb-24 pt-6">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/observe" element={<ObservePage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/expert" element={<ExpertPage />} />
            <Route path="/result/:id" element={<ResultPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <BottomNav />
      </div>
    </BrowserRouter>
  )
}
