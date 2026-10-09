import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function TeamsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const teamsQuery = useQuery({ queryKey: ["teams"], queryFn: api.listTeams });

  const createMutation = useMutation({
    mutationFn: () => api.createTeam({ name, description: description || undefined }),
    onSuccess: () => {
      setName("");
      setDescription("");
      queryClient.invalidateQueries({ queryKey: ["teams"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteTeam(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["teams"] }),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (name.trim()) createMutation.mutate();
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Teams</h1>

      <form onSubmit={onSubmit} className="mb-6 flex gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <input placeholder="Team name" required value={name} onChange={(e) => setName(e.target.value)} className="w-56 rounded-lg border border-slate-300 px-3 py-2" />
        <input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} className="flex-1 rounded-lg border border-slate-300 px-3 py-2" />
        <button type="submit" disabled={createMutation.isPending} className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50">Create</button>
      </form>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(teamsQuery.data || []).map((team) => (
          <TeamCard key={team.id} team={team} onDelete={() => deleteMutation.mutate(team.id)} />
        ))}
        {!teamsQuery.isLoading && (teamsQuery.data || []).length === 0 && (
          <div className="col-span-full py-10 text-center text-slate-500">No teams yet</div>
        )}
      </div>
    </div>
  );
}

function TeamCard({ team, onDelete }: { team: { id: number; name: string; description: string | null; members: { id: number; full_name: string; email: string }[] }; onDelete: () => void }) {
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState("");

  const addMutation = useMutation({
    mutationFn: () => api.addTeamMember(team.id, Number(userId)),
    onSuccess: () => { setUserId(""); queryClient.invalidateQueries({ queryKey: ["teams"] }); },
  });
  const removeMutation = useMutation({
    mutationFn: (memberId: number) => api.removeTeamMember(team.id, memberId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["teams"] }),
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <div className="font-semibold">{team.name}</div>
        <button onClick={onDelete} className="rounded border border-red-300 px-2 py-0.5 text-xs text-red-600 hover:bg-red-50">Delete</button>
      </div>
      <div className="mt-1 text-sm text-slate-500">{team.description || "No description"}</div>
      <div className="mt-3 text-sm text-slate-600">
        <div className="text-xs text-slate-400">Members ({team.members.length})</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {team.members.map((member) => (
            <span key={member.id} className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs">
              {member.full_name || member.email}
              <button onClick={() => removeMutation.mutate(member.id)} className="text-slate-400 hover:text-red-600">✕</button>
            </span>
          ))}
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <input placeholder="User ID" value={userId} onChange={(e) => setUserId(e.target.value)} className="w-24 rounded-lg border border-slate-300 px-2 py-1 text-sm" />
        <button onClick={() => userId && addMutation.mutate()} className="rounded-lg bg-slate-800 px-2 py-1 text-sm text-white">Add member</button>
      </div>
    </div>
  );
}
