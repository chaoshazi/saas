import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { SearchResults } from "../lib/types";

export function SearchBox() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [open, setOpen] = useState(false);

  const searchMutation = useMutation({
    mutationFn: (query: string) => api.search(query),
    onSuccess: (data) => {
      setResults(data);
      setOpen(true);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (q.trim()) searchMutation.mutate(q);
  }

  function go(path: string) {
    setOpen(false);
    setQ("");
    navigate(path);
  }

  return (
    <div className="relative">
      <form onSubmit={onSubmit}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results && setOpen(true)}
          placeholder="Search projects, tasks, docs…"
          className="w-64 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
        />
      </form>
      {open && results && (
        <div
          className="absolute right-0 z-20 mt-1 w-80 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
          onMouseLeave={() => setOpen(false)}
        >
          {results.projects.length === 0 && results.tasks.length === 0 && results.documents.length === 0 && (
            <div className="px-3 py-2 text-sm text-slate-400">No results</div>
          )}
          {results.projects.map((project) => (
            <button key={`p${project.id}`} onClick={() => go(`/projects/${project.id}`)} className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50">
              <span className="font-medium">{project.name}</span>
              <span className="ml-2 text-xs text-slate-400">Project · {project.key}</span>
            </button>
          ))}
          {results.tasks.map((task) => (
            <button key={`t${task.id}`} onClick={() => go(`/projects/${task.project_id}`)} className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50">
              <span className="font-medium">{task.title}</span>
              <span className="ml-2 text-xs text-slate-400">Task · {task.status}</span>
            </button>
          ))}
          {results.documents.map((document) => (
            <button key={`d${document.id}`} onClick={() => go("/documents")} className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50">
              <span className="font-medium">{document.title}</span>
              <span className="ml-2 text-xs text-slate-400">Document</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
