import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { WizardProvider } from './context/WizardContext'
import Settings from './pages/01_Settings'
import HardwareScan from './pages/02_HardwareScan'
import ModelSelection from './pages/03_ModelSelection'
import TopicChat from './pages/04_TopicChat'
import ScrapingConfig from './pages/05_ScrapingConfig'
import ScrapingProgress from './pages/06_ScrapingProgress'
import Preprocessing from './pages/07_Preprocessing'
import ColabConnect from './pages/08_ColabConnect'
import Training from './pages/09_Training'
import Dashboard from './pages/10_Dashboard'

export default function App() {
  return (
    <WizardProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/settings" replace />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/hardware" element={<HardwareScan />} />
          <Route path="/model" element={<ModelSelection />} />
          <Route path="/topic" element={<TopicChat />} />
          <Route path="/scraping/config" element={<ScrapingConfig />} />
          <Route path="/scraping/progress" element={<ScrapingProgress />} />
          <Route path="/preprocessing" element={<Preprocessing />} />
          <Route path="/colab" element={<ColabConnect />} />
          <Route path="/training" element={<Training />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </WizardProvider>
  )
}
