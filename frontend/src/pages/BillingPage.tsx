import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function BillingPage() {
  const plansQuery = useQuery({ queryKey: ["plans"], queryFn: api.listPlans });
  const subscriptionQuery = useQuery({ queryKey: ["subscription"], queryFn: api.getSubscription });

  const subscription = subscriptionQuery.data;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Billing</h1>
      <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5">
        <div className="text-sm text-slate-500">Current subscription</div>
        {subscription ? (
          <div className="mt-2">
            <div className="text-lg font-medium capitalize">{subscription.status}</div>
            <div className="text-sm text-slate-500">
              {new Date(subscription.current_period_start).toLocaleDateString()} →{" "}
              {new Date(subscription.current_period_end).toLocaleDateString()}
            </div>
          </div>
        ) : (
          <div className="mt-2 text-slate-500">No active subscription</div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {(plansQuery.data || []).map((plan) => (
          <div key={plan.id} className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="font-semibold">{plan.name}</div>
            <div className="mt-2 text-2xl font-semibold">
              ¥{(plan.amount_cents / 100).toFixed(2)}
              <span className="text-sm font-normal text-slate-400">/{plan.interval}</span>
            </div>
            <ul className="mt-4 space-y-1 text-sm text-slate-600">
              <li>Up to {plan.max_users} users</li>
              <li>Up to {plan.max_projects} projects</li>
              <li>{plan.max_storage_gb} GB storage</li>
            </ul>
            <button className="mt-4 w-full rounded-lg border border-blue-600 py-2 text-sm font-medium text-blue-600">
              Subscribe
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
