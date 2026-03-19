import { RESEARCH_BASE } from './chat-api';

export interface Project {
  id: string;
  name: string;
  created_at: string;
  status: 'active' | 'archived';
  description: string;
  note_count?: number;
  last_activity?: string;
}

export interface ProjectNote {
  id: string;
  project_id: string;
  text: string;
  audio_file: string | null;
  source: { type: string; id: string; title: string } | null;
  created_at: string;
}

export async function listProjects(): Promise<Project[]> {
  const resp = await fetch(`${RESEARCH_BASE}/projects`);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`List projects failed (${resp.status}): ${text}`);
  }
  const data = await resp.json();
  return data.projects || [];
}

export async function createProject(name: string, description?: string): Promise<Project> {
  const resp = await fetch(`${RESEARCH_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: description || '' }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Create project failed (${resp.status}): ${text}`);
  }
  const data = await resp.json();
  return data.project;
}

export async function getProject(id: string): Promise<{ project: Project; notes: ProjectNote[] }> {
  const resp = await fetch(`${RESEARCH_BASE}/projects/${encodeURIComponent(id)}`);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Get project failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

export async function addProjectNote(
  projectId: string,
  text: string,
  source?: { type: string; id: string; title: string },
): Promise<ProjectNote> {
  const resp = await fetch(`${RESEARCH_BASE}/projects/note`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, text, source: source || null }),
  });
  if (!resp.ok) {
    const errBody = await resp.text();
    throw new Error(`Add note failed (${resp.status}): ${errBody}`);
  }
  const data = await resp.json();
  return data.note;
}

export async function updateProject(
  id: string,
  updates: Partial<Pick<Project, 'name' | 'status' | 'description'>>,
): Promise<Project> {
  const resp = await fetch(`${RESEARCH_BASE}/projects/${encodeURIComponent(id)}/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Update project failed (${resp.status}): ${text}`);
  }
  const data = await resp.json();
  return data.project;
}
