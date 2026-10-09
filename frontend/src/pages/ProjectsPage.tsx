import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(false),
  });

  const createMutation = useMutation({
    mutationFn: () => api.createProject({ name, key, description: description || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setName("");
      setKey("");
      setDescription("");
      setError("");
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Create failed"),
  });

  const archiveMutation = useMutation({
    mutationFn: (id: number) => api.updateProject(id, { is_archived: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteProject(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    createMutation.mutate();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
      </div>

      <form onSubmit={onSubmit} className="mb-6 flex gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <input
          placeholder="Project name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-56 rounded-lg border border-slate-300 px-3 py-2"
        />
        <input
          placeholder="Key (e.g. CRM)"
          required
          value={key}
          onChange={(e) => setKey(e.target.value)}
          className="w-40 rounded-lg border border-slate-300 px-3 py-2"
        />
        <input
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
        />
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Create
        </button>
        {error && <span className="self-center text-sm text-red-600">{error}</span>}
      </form>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(projectsQuery.data?.items || []).map((project) => (
          <div
            key={project.id}
            onClick={() => navigate(`/projects/${project.id}`)}
            className="cursor-pointer rounded-2xl border border-slate-200 bg-white p-5 hover:border-blue-300"
          >
            <div className="flex items-center justify-between">
              <div className="font-semibold">{project.name}</div>
              <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => archiveMutation.mutate(project.id)}
                  className="rounded border border-slate-300 px-2 py-0.5 text-xs hover:bg-slate-50"
                >
                  Archive
                </button>
                <button
                  onClick={() => deleteMutation.mutate(project.id)}
                  className="rounded border border-red-300 px-2 py-0.5 text-xs text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
            <div className="mt-1 text-sm text-slate-500">{project.key}</div>
            <div className="mt-3 text-sm text-slate-600 line-clamp-2">{project.description || "No description"}</div>
          </div>
        ))}
        {!projectsQuery.isLoading && (projectsQuery.data?.items || []).length === 0 && (
          <div className="col-span-full py-10 text-center text-slate-500">No projects yet</div>
        )}
      </div>
    </div>
  );
}
