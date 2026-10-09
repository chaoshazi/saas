import { FormEvent, useState } from "react";
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Label, Task } from "../lib/types";

export function ProjectBoardPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const queryClient = useQueryClient();
  const [newTitle, setNewTitle] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [showMembers, setShowMembers] = useState(false);
  const [showActivity, setShowActivity] = useState(false);

  const projectQuery = useQuery({ queryKey: ["project", id], queryFn: () => api.getProject(id), enabled: Number.isFinite(id) });
  const boardsQuery = useQuery({ queryKey: ["boards", id], queryFn: () => api.listBoards(id), enabled: Number.isFinite(id) });
  const tasksQuery = useQuery({ queryKey: ["tasks", id], queryFn: () => api.listTasks(id), enabled: Number.isFinite(id) });
  const membersQuery = useQuery({ queryKey: ["project-members", id], queryFn: () => api.listProjectMembers(id), enabled: Number.isFinite(id) });
  const activitiesQuery = useQuery({ queryKey: ["activities", id], queryFn: () => api.listActivities(id), enabled: Number.isFinite(id) });

  const createTaskMutation = useMutation({
    mutationFn: () => {
      const board = boardsQuery.data?.[0];
      return api.createTask({ board_id: board!.id, column_id: board?.columns[0]?.id ?? null, title: newTitle });
    },
    onSuccess: () => {
      setNewTitle("");
      queryClient.invalidateQueries({ queryKey: ["tasks", id] });
      queryClient.invalidateQueries({ queryKey: ["activities", id] });
    },
  });

  const moveTaskMutation = useMutation({
    mutationFn: ({ task, columnId }: { task: Task; columnId: number | null }) =>
      api.updateTask(task.id, { column_id: columnId, version: task.version }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks", id] }),
  });

  const selectedTask = (tasksQuery.data || []).find((task) => task.id === selectedTaskId);

  function submitTask(event: FormEvent) {
    event.preventDefault();
    if (newTitle.trim()) createTaskMutation.mutate();
  }

  function tasksForColumn(columnId: number | null): Task[] {
    return (tasksQuery.data || []).filter((task) => task.column_id === columnId);
  }

  return (
    <div className="flex h-full gap-6">
      <div className="min-w-0 flex-1">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">{projectQuery.data?.name || "Board"}</h1>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowMembers(!showMembers)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm">Members</button>
            <button onClick={() => setShowActivity(!showActivity)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm">Activity</button>
            <form onSubmit={submitTask} className="flex gap-2">
              <input placeholder="New task title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} className="w-72 rounded-lg border border-slate-300 px-3 py-2" />
              <button type="submit" disabled={createTaskMutation.isPending || !boardsQuery.data?.[0]} className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50">Add</button>
            </form>
          </div>
        </div>

        {showMembers && <MembersPanel projectId={id} />}
        {showActivity && <ActivityPanel projectId={id} />}

        <div className="flex gap-4 overflow-x-auto pb-4">
          {(boardsQuery.data || []).map((board) => (
            <div key={board.id} className="w-72 shrink-0">
              <div className="mb-3 rounded-xl bg-slate-800 px-4 py-2 text-white">{board.name}</div>
              {board.columns.map((column) => (
                <div key={column.id} className="mb-4">
                  <div className="mb-2 flex items-center justify-between px-1">
                    <span className="text-sm font-medium text-slate-600">{column.name}</span>
                    <span className="text-xs text-slate-400">{tasksForColumn(column.id).length}</span>
                  </div>
                  <div className="space-y-2">
                    {tasksForColumn(column.id).map((task) => (
                      <div key={task.id} onClick={() => setSelectedTaskId(task.id)} className="cursor-pointer rounded-xl border border-slate-200 bg-white p-3 shadow-sm hover:border-blue-300">
                        <div className="font-medium">{task.title}</div>
                        <div className="mt-2 flex items-center justify-between">
                          <span className={`rounded px-2 py-0.5 text-xs ${task.priority === "high" ? "bg-red-100 text-red-700" : task.priority === "low" ? "bg-slate-100 text-slate-600" : "bg-blue-100 text-blue-700"}`}>{task.priority}</span>
                          <select value={task.column_id ?? ""} onClick={(e) => e.stopPropagation()} onChange={(e) => moveTaskMutation.mutate({ task, columnId: e.target.value ? Number(e.target.value) : null })} className="rounded border border-slate-200 px-1 py-0.5 text-xs">
                            <option value="">Backlog</option>
                            {board.columns.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
                          </select>
                        </div>
                      </div>
                    ))}
                    {tasksForColumn(column.id).length === 0 && <div className="rounded-xl border border-dashed border-slate-200 p-3 text-center text-xs text-slate-400">No tasks</div>}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {selectedTask && <TaskDetailPanel task={selectedTask} onClose={() => setSelectedTaskId(null)} />}
    </div>
  );
}

function MembersPanel({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("member");

  const membersQuery = useQuery({ queryKey: ["project-members", projectId], queryFn: () => api.listProjectMembers(projectId) });
  const addMutation = useMutation({
    mutationFn: () => api.addProjectMember(projectId, Number(userId), role),
    onSuccess: () => { setUserId(""); queryClient.invalidateQueries({ queryKey: ["project-members", projectId] }); },
  });
  const removeMutation = useMutation({
    mutationFn: (memberId: number) => api.removeProjectMember(projectId, memberId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project-members", projectId] }),
  });

  return (
    <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex gap-2">
        <input placeholder="User ID" value={userId} onChange={(e) => setUserId(e.target.value)} className="w-28 rounded-lg border border-slate-300 px-3 py-1.5 text-sm" />
        <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm">
          <option value="member">member</option>
          <option value="admin">admin</option>
          <option value="viewer">viewer</option>
        </select>
        <button onClick={() => userId && addMutation.mutate()} className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-white">Add</button>
      </div>
      <div className="flex flex-wrap gap-2">
        {(membersQuery.data || []).map((member) => (
          <span key={member.id} className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2 py-1 text-xs">
            user #{member.user_id} · {member.role}
            <button onClick={() => removeMutation.mutate(member.id)} className="text-slate-400 hover:text-red-600">✕</button>
          </span>
        ))}
      </div>
    </div>
  );
}

function ActivityPanel({ projectId }: { projectId: number }) {
  const activitiesQuery = useQuery({ queryKey: ["activities", projectId], queryFn: () => api.listActivities(projectId) });
  return (
    <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="space-y-2">
        {(activitiesQuery.data || []).map((activity) => (
          <div key={activity.id} className="flex items-center justify-between text-sm">
            <span>
              <span className="font-medium">{activity.actor_name || activity.actor_id || "—"}</span>
              <span className="ml-2 text-slate-500">{activity.action}</span>
            </span>
            <span className="text-xs text-slate-400">{new Date(activity.created_at).toLocaleString()}</span>
          </div>
        ))}
        {(activitiesQuery.data || []).length === 0 && <div className="text-sm text-slate-400">No activity yet</div>}
      </div>
    </div>
  );
}

function TaskDetailPanel({ task, onClose }: { task: Task; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description ?? "");
  const [priority, setPriority] = useState(task.priority);
  const [status, setStatus] = useState(task.status);
  const [comment, setComment] = useState("");
  const [subtaskTitle, setSubtaskTitle] = useState("");
  const [labelName, setLabelName] = useState("");

  const commentsQuery = useQuery({ queryKey: ["comments", task.id], queryFn: () => api.listComments(task.id) });
  const subtasksQuery = useQuery({ queryKey: ["subtasks", task.id], queryFn: () => api.listSubtasks(task.id) });
  const taskLabelsQuery = useQuery({ queryKey: ["task-labels", task.id], queryFn: () => api.listTaskLabels(task.id) });
  const projectLabelsQuery = useQuery({ queryKey: ["labels", task.project_id], queryFn: () => api.listLabels(task.project_id) });

  const saveMutation = useMutation({
    mutationFn: () => api.updateTask(task.id, { title, description, priority, status, version: task.version }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const deleteMutation = useMutation({
    mutationFn: () => api.deleteTask(task.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tasks"] }); onClose(); },
  });
  const addCommentMutation = useMutation({
    mutationFn: () => api.addComment(task.id, comment),
    onSuccess: () => { setComment(""); queryClient.invalidateQueries({ queryKey: ["comments", task.id] }); },
  });
  const addSubtaskMutation = useMutation({
    mutationFn: () => api.createSubtask(task.id, { title: subtaskTitle }),
    onSuccess: () => { setSubtaskTitle(""); queryClient.invalidateQueries({ queryKey: ["subtasks", task.id] }); queryClient.invalidateQueries({ queryKey: ["tasks"] }); },
  });
  const createLabelMutation = useMutation({
    mutationFn: () => api.createLabel(task.project_id, { name: labelName }),
    onSuccess: (label) => { setLabelName(""); queryClient.invalidateQueries({ queryKey: ["labels", task.project_id] }); queryClient.invalidateQueries({ queryKey: ["task-labels", task.id] }); api.assignLabel(task.id, label.id).then(() => queryClient.invalidateQueries({ queryKey: ["task-labels", task.id] })); },
  });
  const toggleLabelMutation = useMutation({
    mutationFn: async ({ label, assign }: { label: Label; assign: boolean }) => {
      if (assign) await api.assignLabel(task.id, label.id);
      else await api.removeLabel(task.id, label.id);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task-labels", task.id] }),
  });

  const assignedIds = new Set((taskLabelsQuery.data || []).map((l) => l.id));

  return (
    <div className="w-80 shrink-0 rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-start justify-between">
        <div className="text-sm text-slate-500">#{task.id} · v{task.version}</div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700">✕</button>
      </div>

      <input value={title} onChange={(e) => setTitle(e.target.value)} className="mb-3 w-full text-lg font-semibold outline-none" />
      <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" className="mb-3 w-full rounded-lg border border-slate-200 p-2 text-sm" rows={3} />

      <div className="mb-4 flex gap-2">
        <select value={priority} onChange={(e) => setPriority(e.target.value)} className="rounded-lg border border-slate-300 px-2 py-1 text-sm">
          <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-slate-300 px-2 py-1 text-sm">
          <option value="open">Open</option><option value="in_progress">In progress</option><option value="done">Done</option>
        </select>
      </div>

      <div className="mb-4 flex gap-2">
        <button onClick={() => saveMutation.mutate()} className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white">Save</button>
        <button onClick={() => deleteMutation.mutate()} className="rounded-lg border border-red-300 px-3 py-2 text-sm text-red-600">Delete</button>
      </div>

      <Section title="Labels">
        <div className="flex flex-wrap gap-1">
          {(projectLabelsQuery.data || []).map((label) => (
            <button key={label.id} onClick={() => toggleLabelMutation.mutate({ label, assign: !assignedIds.has(label.id) })} className={`rounded-full px-2 py-0.5 text-xs ${assignedIds.has(label.id) ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"}`}>{label.name}</button>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input value={labelName} onChange={(e) => setLabelName(e.target.value)} placeholder="New label" className="flex-1 rounded-lg border border-slate-300 px-2 py-1 text-sm" />
          <button onClick={() => labelName.trim() && createLabelMutation.mutate()} className="rounded-lg bg-slate-800 px-2 py-1 text-sm text-white">Add</button>
        </div>
      </Section>

      <Section title="Subtasks">
        <div className="space-y-1">
          {(subtasksQuery.data || []).map((sub) => (
            <div key={sub.id} className="flex items-center justify-between rounded bg-slate-50 px-2 py-1 text-sm">
              <span>{sub.title}</span>
              <span className="text-xs text-slate-400">{sub.priority}</span>
            </div>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input value={subtaskTitle} onChange={(e) => setSubtaskTitle(e.target.value)} placeholder="New subtask" className="flex-1 rounded-lg border border-slate-300 px-2 py-1 text-sm" />
          <button onClick={() => subtaskTitle.trim() && addSubtaskMutation.mutate()} className="rounded-lg bg-slate-800 px-2 py-1 text-sm text-white">Add</button>
        </div>
      </Section>

      <Section title="Comments">
        <div className="space-y-3">
          {(commentsQuery.data || []).map((item) => (
            <div key={item.id} className="rounded-lg bg-slate-50 p-3">
              <div className="text-xs text-slate-500">{item.author.full_name}</div>
              <div className="mt-1 text-sm">{item.body}</div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex gap-2">
          <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add comment" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button onClick={() => comment.trim() && addCommentMutation.mutate()} className="rounded-lg bg-slate-800 px-3 py-2 text-sm text-white">Send</button>
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mt-6">
      <h3 className="mb-2 text-sm font-medium">{title}</h3>
      {children}
    </div>
  );
}
