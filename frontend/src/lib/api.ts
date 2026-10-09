import type {
  ActivityItem,
  AuditEntry,
  Board,
  DashboardStats,
  Document,
  DocumentVersion,
  Label,
  License,
  Notification,
  NotificationPreference,
  Page,
  Plan,
  Project,
  SearchResults,
  Subscription,
  SystemConfig,
  Task,
  TaskComment,
  Team,
  TokenPair,
  User,
} from "./types";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function getToken(): string | null {
  return localStorage.getItem("access_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.error?.message || data?.detail || `Request failed (${response.status})`;
    throw new ApiError(response.status, data?.error?.code || "error", message);
  }
  return data as T;
}

export const api = {
  // auth
  register: (payload: { email: string; password: string; full_name: string }) =>
    request<TokenPair>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string; totp_code?: string }) =>
    request<TokenPair>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<User>("/auth/me"),
  totpSetup: () => request<{ secret: string; otpauth_uri: string }>("/auth/totp/setup"),
  totpEnable: (code: string) => request<void>("/auth/totp/enable", { method: "POST", body: JSON.stringify({ code }) }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),

  // projects
  listProjects: (archived?: boolean) =>
    request<Page<Project>>(`/projects?archived=${archived ?? false}`),
  createProject: (payload: { name: string; key: string; description?: string }) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  getProject: (id: number) => request<Project>(`/projects/${id}`),
  updateProject: (id: number, payload: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (id: number) => request<void>(`/projects/${id}`, { method: "DELETE" }),

  // boards & tasks
  listBoards: (projectId: number) => request<Board[]>(`/projects/${projectId}/boards`),
  listTasks: (projectId: number) => request<Task[]>(`/tasks?project_id=${projectId}`),
  createTask: (payload: { board_id: number; column_id?: number | null; title: string; priority?: string }) =>
    request<Task>("/tasks", { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (id: number, payload: Partial<Task>) =>
    request<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteTask: (id: number) => request<void>(`/tasks/${id}`, { method: "DELETE" }),
  listComments: (taskId: number) => request<TaskComment[]>(`/tasks/${taskId}/comments`),
  addComment: (taskId: number, body: string) =>
    request<TaskComment>(`/tasks/${taskId}/comments`, { method: "POST", body: JSON.stringify({ body }) }),

  // documents
  listDocuments: (projectId?: number) =>
    request<Document[]>(`/documents${projectId ? `?project_id=${projectId}` : ""}`),
  createDocument: (payload: { project_id?: number | null; title: string; content?: string }) =>
    request<Document>("/documents", { method: "POST", body: JSON.stringify(payload) }),
  getDocument: (id: number) => request<Document>(`/documents/${id}`),
  updateDocument: (id: number, payload: { title?: string; content?: string; change_note?: string }) =>
    request<Document>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listDocumentVersions: (id: number) => request<DocumentVersion[]>(`/documents/${id}/versions`),

  // notifications
  listNotifications: (unreadOnly = false) =>
    request<Page<Notification>>(`/notifications?unread_only=${unreadOnly}`),
  markNotificationRead: (id: number, isRead = true) =>
    request<Notification>(`/notifications/${id}?is_read=${isRead}`, { method: "PATCH" }),
  markAllNotificationsRead: () => request<void>("/notifications/read-all", { method: "POST" }),

  // billing & license
  listPlans: () => request<Plan[]>("/billing/plans"),
  getSubscription: () => request<Subscription | null>("/billing/subscription"),
  getLicense: () => request<License | null>("/license/status"),
  activateLicense: (key: string, fingerprint?: string) =>
    request<License>("/license/activate", { method: "POST", body: JSON.stringify({ key, fingerprint }) }),

  // admin
  listUsers: (page = 1, pageSize = 50) => request<Page<User>>(`/users?page=${page}&page_size=${pageSize}`),
  createUser: (payload: { email: string; password: string; full_name: string }) =>
    request<User>("/users", { method: "POST", body: JSON.stringify(payload) }),
  deactivateUser: (id: number) => request<void>(`/users/${id}`, { method: "DELETE" }),
  grantSuperuser: (id: number) => request<void>(`/users/${id}/superuser`, { method: "POST" }),
  listAudit: (page = 1, pageSize = 50) => request<Page<AuditEntry>>(`/admin/audit?page=${page}&page_size=${pageSize}`),

  // teams
  listTeams: () => request<Team[]>("/teams"),
  createTeam: (payload: { name: string; description?: string }) =>
    request<Team>("/teams", { method: "POST", body: JSON.stringify(payload) }),
  updateTeam: (id: number, payload: { name?: string; description?: string }) =>
    request<Team>(`/teams/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteTeam: (id: number) => request<void>(`/teams/${id}`, { method: "DELETE" }),
  addTeamMember: (teamId: number, userId: number) =>
    request<Team>(`/teams/${teamId}/members?user_id=${userId}`, { method: "POST" }),
  removeTeamMember: (teamId: number, userId: number) =>
    request<void>(`/teams/${teamId}/members/${userId}`, { method: "DELETE" }),

  // labels & project members
  listLabels: (projectId: number) => request<Label[]>(`/projects/${projectId}/labels`),
  createLabel: (projectId: number, payload: { name: string; color?: string }) =>
    request<Label>(`/projects/${projectId}/labels`, { method: "POST", body: JSON.stringify(payload) }),
  listTaskLabels: (taskId: number) => request<Label[]>(`/tasks/${taskId}/labels`),
  assignLabel: (taskId: number, labelId: number) =>
    request<Label>(`/tasks/${taskId}/labels?label_id=${labelId}`, { method: "POST" }),
  removeLabel: (taskId: number, labelId: number) =>
    request<void>(`/tasks/${taskId}/labels/${labelId}`, { method: "DELETE" }),
  listProjectMembers: (projectId: number) => request<{ id: number; project_id: number; user_id: number; role: string }[]>(`/projects/${projectId}/members`),
  addProjectMember: (projectId: number, userId: number, role: string) =>
    request<{ id: number; project_id: number; user_id: number; role: string }>(`/projects/${projectId}/members?user_id=${userId}&role=${role}`, { method: "POST" }),
  updateProjectMember: (projectId: number, memberId: number, role: string) =>
    request<{ id: number; project_id: number; user_id: number; role: string }>(`/projects/${projectId}/members/${memberId}?role=${role}`, { method: "PATCH" }),
  removeProjectMember: (projectId: number, memberId: number) =>
    request<void>(`/projects/${projectId}/members/${memberId}`, { method: "DELETE" }),
  listActivities: (projectId: number) => request<ActivityItem[]>(`/projects/${projectId}/activities`),

  // subtasks
  listSubtasks: (taskId: number) => request<Task[]>(`/tasks/${taskId}/subtasks`),
  createSubtask: (taskId: number, payload: { title: string; assignee_id?: number | null; priority?: string }) =>
    request<Task>(`/tasks/${taskId}/subtasks`, { method: "POST", body: JSON.stringify(payload) }),

  // preferences, stats, search, system
  listNotificationPreferences: () => request<NotificationPreference[]>("/notifications/preferences"),
  updateNotificationPreference: (channel: string, eventType: string, enabled: boolean) =>
    request<NotificationPreference>("/notifications/preferences", { method: "PUT", body: JSON.stringify({ channel, event_type: eventType, enabled }) }),
  dashboardStats: () => request<DashboardStats>("/dashboard/stats"),
  search: (q: string) => request<SearchResults>(`/search?q=${encodeURIComponent(q)}`),
  systemConfig: () => request<SystemConfig>("/system/config"),
  requestPasswordReset: (email: string) =>
    request<{ message: string; token?: string }>("/auth/password/reset-request", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (token: string, newPassword: string) =>
    request<void>("/auth/password/reset", { method: "POST", body: JSON.stringify({ token, new_password: newPassword }) }),
  uploadAvatar: async (file: File): Promise<User> => {
    const form = new FormData();
    form.append("file", file);
    const token = getToken();
    const response = await fetch(`${API_BASE}/users/me/avatar`, {
      method: "PUT",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: form,
    });
    if (!response.ok) throw new ApiError(response.status, "error", "Upload failed");
    return response.json();
  },};
