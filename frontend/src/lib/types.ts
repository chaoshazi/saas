export interface User {
  id: number;
  email: string;
  full_name: string;
  avatar_url: string | null;
  locale: string;
  is_active: boolean;
  is_superuser: boolean;
  totp_enabled: boolean;
  role_slugs: string[];
  permission_codes: string[];
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Project {
  id: number;
  name: string;
  key: string;
  description: string | null;
  owner_id: number;
  is_archived: boolean;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface BoardColumn {
  id: number;
  board_id: number;
  name: string;
  position: number;
  color: string | null;
}

export interface Board {
  id: number;
  project_id: number;
  name: string;
  position: number;
  columns: BoardColumn[];
}

export interface Task {
  id: number;
  project_id: number;
  column_id: number | null;
  parent_id: number | null;
  assignee_id: number | null;
  creator_id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  position: number;
  due_date: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  assignee: User | null;
  creator: User;
}

export interface TaskComment {
  id: number;
  task_id: number;
  author_id: number;
  body: string;
  created_at: string;
  author: User;
}

export interface Notification {
  id: number;
  user_id: number;
  actor_id: number | null;
  title: string;
  body: string | null;
  type: string;
  resource_type: string | null;
  resource_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface Plan {
  id: number;
  code: string;
  name: string;
  interval: string;
  amount_cents: number;
  currency: string;
  max_users: number;
  max_projects: number;
  max_storage_gb: number;
  is_active: boolean;
}

export interface Subscription {
  id: number;
  plan_id: number;
  status: string;
  current_period_start: string;
  current_period_end: string;
  auto_renew: boolean;
}

export interface Document {
  id: number;
  project_id: number | null;
  creator_id: number;
  title: string;
  content: string | null;
  is_published: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  creator: User;
}

export interface DocumentVersion {
  id: number;
  document_id: number;
  author_id: number;
  version: number;
  content: string | null;
  change_note: string | null;
  created_at: string;
}

export interface AuditEntry {
  id: number;
  actor_id: number | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface License {
  id: number;
  key: string;
  status: string;
  plan_code: string;
  issued_to: string | null;
  issued_at: string | null;
  expires_at: string | null;
  last_checked_at: string | null;
}

export interface Page<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface Team {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
  owner: User;
  members: User[];
}

export interface Label {
  id: number;
  project_id: number;
  name: string;
  color: string | null;
  created_at: string;
}

export interface ActivityItem {
  id: number;
  actor_id: number | null;
  actor_name: string | null;
  action: string;
  target_type: string;
  target_id: string;
  created_at: string;
}

export interface NotificationPreference {
  id: number;
  user_id: number;
  channel: string;
  event_type: string;
  enabled: boolean;
}

export interface DashboardStats {
  projects: number;
  tasks: number;
  unread_notifications: number;
  users: number;
  teams: number;
}

export interface SearchResults {
  projects: { id: number; name: string; key: string }[];
  tasks: { id: number; project_id: number; title: string; status: string }[];
  documents: { id: number; project_id: number | null; title: string }[];
}

export interface SystemConfig {
  app_name: string;
  version: string;
  app_env: string;
  registration_open: boolean;
  sso: { wecom_enabled: boolean };
  payments: { alipay_enabled: boolean; wechat_enabled: boolean };
  totp_issuer: string;
  demo: {
    admin_email: string;
    admin_password: string;
    demo_password: string;
    demo_emails: string[];
  } | null;
}
