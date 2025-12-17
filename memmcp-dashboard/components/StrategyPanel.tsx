interface StrategyEntry {
  name?: string;
  capital?: number;
  win_rate?: number | null;
  daily_pnl?: number | null;
  notes?: string | null;
  memory_ref?: string | null;
}

interface Props {
  strategies: {
    updatedAt?: string | null;
    strategies?: StrategyEntry[];
  } | null;
}

export function StrategyPanel({ strategies }: Props) {
  const rows = strategies?.strategies ?? [];
  if (!rows.length) {
    return (
      <section className="card">
        <h2 className="text-xl font-semibold">Strategy Heatmap</h2>
        <p className="text-sm text-slate-400">No strategy telemetry received yet.</p>
      </section>
    );
  }

  return (
    <section className="card space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Strategy Heatmap</h2>
        {strategies?.updatedAt && (
          <span className="text-xs text-slate-400">
            Updated {new Date(strategies.updatedAt).toLocaleTimeString()}
          </span>
        )}
      </div>
      <div className="overflow-x-auto text-sm">
        <table className="w-full border border-slate-700/60 rounded">
          <thead className="bg-slate-900/40 text-slate-300">
            <tr>
              <th className="px-3 py-2 text-left">Strategy</th>
              <th className="px-3 py-2 text-right">Capital</th>
              <th className="px-3 py-2 text-right">Win Rate</th>
              <th className="px-3 py-2 text-right">Daily PnL</th>
              <th className="px-3 py-2 text-left">Notes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const winRate = row.win_rate ?? null;
              const pnl = row.daily_pnl ?? null;
              return (
                <tr key={`${row.name}-${idx}`} className="border-t border-slate-800">
                  <td className="px-3 py-2 font-medium">
                    <div>{row.name ?? `Strategy ${idx + 1}`}</div>
                    {row.memory_ref && (
                      <a
                        href={row.memory_ref}
                        className="text-xs text-amber-300 hover:underline"
                        target="_blank"
                        rel="noreferrer"
                      >
                        memory trace
                      </a>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    ${(row.capital ?? 0).toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {winRate !== null ? `${(winRate * 100).toFixed(1)}%` : "—"}
                  </td>
                  <td
                    className={`px-3 py-2 text-right ${
                      pnl !== null && pnl < 0 ? "text-rose-300" : "text-emerald-300"
                    }`}
                  >
                    {pnl !== null ? `$${pnl.toFixed(2)}` : "—"}
                  </td>
                  <td className="px-3 py-2 text-left text-slate-300">
                    {row.notes ?? ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
