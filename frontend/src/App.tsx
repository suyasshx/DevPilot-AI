import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { OverviewView } from './components/OverviewView';
import { SpecsView } from './components/SpecsView';
import { KnowledgeView } from './components/KnowledgeView';
import { WorkflowLaunchView } from './components/WorkflowLaunchView';
import { RunsView } from './components/RunsView';
import { ProjectModal } from './components/ProjectModal';
import { api } from './services/api';
import { Project, ApiSpecification, ApiEndpoint, KnowledgeDocument, TestRun } from './types/api';

export function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);

  // Project Artifacts State
  const [specs, setSpecs] = useState<ApiSpecification[]>([]);
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [runs, setRuns] = useState<TestRun[]>([]);

  // Cross-Tab Selections
  const [workflowEndpoint, setWorkflowEndpoint] = useState<ApiEndpoint | null>(null);
  const [targetRunId, setTargetRunId] = useState<string | null>(null);

  // Initial Load of Projects
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const projs = await api.getProjects();
      setProjects(projs);
      if (projs.length > 0 && !selectedProject) {
        setSelectedProject(projs[0]);
      } else if (projs.length === 0) {
        // Auto-initialize a default project so the user has an immediate workspace
        const initial = await api.createProject('My API Project', 'Universal API Testing Workspace');
        setProjects([initial]);
        setSelectedProject(initial);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  // Reload artifacts when selected project changes
  useEffect(() => {
    if (!selectedProject) return;
    refreshProjectData(selectedProject.id);
  }, [selectedProject]);

  const refreshProjectData = async (projectId: string) => {
    try {
      const [specList, epList, docList, runList] = await Promise.all([
        api.getSpecs(projectId).catch(() => []),
        api.getEndpoints(projectId).catch(() => []),
        api.getDocuments(projectId).catch(() => []),
        api.getRuns(projectId).catch(() => ({ total: 0, items: [] })),
      ]);

      setSpecs(specList);
      setEndpoints(epList);
      setDocuments(docList);
      setRuns(runList.items || []);
    } catch (err) {
      console.error('Failed to refresh project data:', err);
    }
  };

  const handleEndpointSelectForTest = (ep: ApiEndpoint) => {
    setWorkflowEndpoint(ep);
    setCurrentTab('workflow');
  };

  const handleRunFinished = (runId: string) => {
    if (selectedProject) {
      refreshProjectData(selectedProject.id);
    }
    setTargetRunId(runId);
    setCurrentTab('runs');
  };

  if (!selectedProject) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-base)' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          <div className="animate-spin" style={{ width: '32px', height: '32px', border: '3px solid var(--accent-cyan)', borderTopColor: 'transparent', borderRadius: '50%', margin: '0 auto 16px' }} />
          <div>Loading DevPilot AI Platform...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container" id="app-root">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        projects={projects}
        selectedProject={selectedProject}
        onSelectProject={(p) => {
          setSelectedProject(p);
          setWorkflowEndpoint(null);
          setTargetRunId(null);
        }}
        onOpenNewProjectModal={() => setIsNewProjectModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="main-content" id="main-content-viewport">
        {currentTab === 'overview' && (
          <OverviewView
            project={selectedProject}
            specs={specs}
            endpoints={endpoints}
            documents={documents}
            runs={runs}
            onNavigate={setCurrentTab}
          />
        )}

        {currentTab === 'specs' && (
          <SpecsView
            project={selectedProject}
            specs={specs}
            endpoints={endpoints}
            onSpecUploaded={() => refreshProjectData(selectedProject.id)}
            onSelectEndpointForTest={handleEndpointSelectForTest}
          />
        )}

        {currentTab === 'knowledge' && (
          <KnowledgeView
            project={selectedProject}
            documents={documents}
            onDocumentAdded={() => refreshProjectData(selectedProject.id)}
          />
        )}

        {currentTab === 'workflow' && (
          <WorkflowLaunchView
            project={selectedProject}
            endpoints={endpoints}
            selectedEndpoint={workflowEndpoint}
            onSelectEndpoint={setWorkflowEndpoint}
            onRunFinished={handleRunFinished}
          />
        )}

        {currentTab === 'runs' && (
          <RunsView
            project={selectedProject}
            runs={runs}
            initialRunId={targetRunId}
            onRefreshRuns={() => refreshProjectData(selectedProject.id)}
          />
        )}
      </main>

      {/* New Project Modal */}
      <ProjectModal
        isOpen={isNewProjectModalOpen}
        onClose={() => setIsNewProjectModalOpen(false)}
        onProjectCreated={(newProj) => {
          setProjects((prev) => [...prev, newProj]);
          setSelectedProject(newProj);
        }}
      />
    </div>
  );
}

export default App;
