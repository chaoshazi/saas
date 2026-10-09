import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Document } from "../lib/types";

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: () => api.listDocuments() });

  const createMutation = useMutation({
    mutationFn: () => api.createDocument({ title, content: content || undefined }),
    onSuccess: (doc) => {
      setTitle("");
      setContent("");
      setSelectedId(doc.id);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (title.trim()) createMutation.mutate();
  }

  const selected = (documentsQuery.data || []).find((doc) => doc.id === selectedId);

  return (
    <div className="flex h-full gap-6">
      <div className="w-80 shrink-0">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Documents</h1>
        </div>
        <form onSubmit={onSubmit} className="mb-4 rounded-2xl border border-slate-200 bg-white p-4">
          <input
            placeholder="Document title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
          <textarea
            placeholder="Content (optional)"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            rows={3}
          />
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="w-full rounded-lg bg-blue-600 py-2 font-medium text-white disabled:opacity-50"
          >
            Create
          </button>
        </form>
        <div className="space-y-2">
          {(documentsQuery.data || []).map((doc) => (
            <button
              key={doc.id}
              onClick={() => setSelectedId(doc.id)}
              className={`block w-full rounded-xl border bg-white p-3 text-left ${
                selectedId === doc.id ? "border-blue-400" : "border-slate-200"
              }`}
            >
              <div className="truncate font-medium">{doc.title}</div>
              <div className="mt-1 text-xs text-slate-400">
                v{doc.version} · {doc.creator.full_name}
              </div>
            </button>
          ))}
          {!documentsQuery.isLoading && (documentsQuery.data || []).length === 0 && (
            <div className="py-8 text-center text-sm text-slate-500">No documents</div>
          )}
        </div>
      </div>

      {selected && <DocumentEditor document={selected} onClose={() => setSelectedId(null)} />}
    </div>
  );
}

function DocumentEditor({ document, onClose }: { document: Document; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(document.title);
  const [content, setContent] = useState(document.content ?? "");
  const [changeNote, setChangeNote] = useState("");

  const versionsQuery = useQuery({
    queryKey: ["document-versions", document.id],
    queryFn: () => api.listDocumentVersions(document.id),
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateDocument(document.id, { title, content, change_note: changeNote || undefined }),
    onSuccess: (updated) => {
      setChangeNote("");
      setTitle(updated.title);
      setContent(updated.content ?? "");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["document-versions", document.id] });
    },
  });

  return (
    <div className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="text-xl font-semibold outline-none"
        />
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
          ✕
        </button>
      </div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="h-72 w-full rounded-xl border border-slate-200 p-3 text-sm"
        placeholder="Write documentation..."
      />
      <div className="mt-3 flex items-center gap-2">
        <input
          value={changeNote}
          onChange={(e) => setChangeNote(e.target.value)}
          placeholder="Change note (optional)"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Save (new version)
        </button>
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-sm font-medium">Version history</h3>
        <div className="space-y-2">
          {(versionsQuery.data || []).map((version) => (
            <div key={version.id} className="rounded-lg bg-slate-50 p-3 text-sm">
              <span className="font-medium">v{version.version}</span>
              <span className="ml-2 text-xs text-slate-400">{new Date(version.created_at).toLocaleString()}</span>
              {version.change_note && <div className="mt-1 text-slate-600">{version.change_note}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
