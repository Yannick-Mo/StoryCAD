import { Routes, Route, Navigate } from 'react-router-dom'
import ProjectListPage from './pages/home'
import ProjectPage from './pages/editor'
import { ProjectProvider } from './context/ProjectContext'

export default function App() {
  return (
    <ProjectProvider>
      <Routes>
        <Route path="/" element={<ProjectListPage />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ProjectProvider>
  )
}
