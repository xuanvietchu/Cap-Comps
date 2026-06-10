import { Comp } from "../types";
import { formatCurrency, formatPerSqft, honestDoorUrl } from "../utils";

function ScoreMini({
  label,
  value,
  subtitle,
  tone,
}: {
  label: string;
  value?: number | null;
  subtitle: string;
  tone: string;
}) {
  const percent = Math.max(0, Math.min(100, (value ?? 0) * 100));

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-slate-500">
        <span>{label}</span>
        <span>{percent.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full ${tone}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="text-[10px] leading-4 text-slate-500">{subtitle}</div>
    </div>
  );
}

export default function CompsTable({ comps }: { comps: Comp[] }) {
  return (
    <div className="max-w-5xl overflow-hidden rounded-2xl border border-white/10 bg-[#111827]">
      <div className="border-b border-white/10 px-5 py-4">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
          Ranked comps
        </p>
      </div>

      <div className="max-h-[520px] overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-slate-400">
            <tr>
              <th className="w-10 px-3 py-3 text-right font-medium">#</th>
              <th className="px-4 py-3 text-left font-medium">Address</th>
              <th className="px-4 py-3 text-right font-medium">Sold price</th>
              <th className="px-4 py-3 text-left font-medium">Built</th>
              <th className="px-4 py-3 text-left font-medium">Sold date</th>
              <th className="px-4 py-3 text-right font-medium">Distance</th>
              <th className="px-4 py-3 text-right font-medium">
                Score (Attr. + Price)
              </th>
            </tr>
          </thead>
          <tbody>
            {comps.map((comp, index) => (
              <tr
                key={`${comp.address}-${index}`}
                className="border-t border-white/10"
              >
                <td className="w-10 px-3 py-4 text-right text-xs text-slate-500">
                  {index + 1}
                </td>
                <td className="px-4 py-4 text-slate-100">
                  <a
                    href={honestDoorUrl(comp.address)}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-blue-200 underline decoration-blue-300/40 underline-offset-4 transition hover:text-blue-100 hover:decoration-blue-200"
                  >
                    {comp.address}
                  </a>
                </td>
                <td className="px-4 py-4 text-right text-slate-100">
                  {formatCurrency(comp.sold_price)}
                </td>
                <td className="px-4 py-4 text-slate-400">
                  {comp.yearBuilt ?? "n/a"}
                </td>
                <td className="px-4 py-4 text-slate-400">
                  {comp.sold_date || "n/a"}
                </td>
                <td className="px-4 py-4 text-right text-slate-400">
                  {comp.distance_km === null || comp.distance_km === undefined
                    ? "n/a"
                    : `${comp.distance_km.toFixed(1)} km`}
                </td>
                <td className="px-4 py-4 text-right text-slate-100">
                  <div className="flex flex-col items-end gap-2">
                    <span>
                      {((comp.similarity_score ?? 0) * 100).toFixed(1)}%
                    </span>
                    <div className="w-40 space-y-2">
                      <ScoreMini
                        label="Attributes"
                        value={comp.leaf_similarity_score}
                        tone="bg-gradient-to-r from-emerald-400 to-teal-400"
                        subtitle={
                          comp.leaf_matches !== null &&
                          comp.leaf_matches !== undefined &&
                          comp.leaf_count
                            ? `${comp.leaf_matches}/${comp.leaf_count} leaves`
                            : "Leaf overlap"
                        }
                      />
                      <ScoreMini
                        label="$/SQFT"
                        value={comp.price_per_sqft_similarity}
                        tone="bg-gradient-to-r from-amber-400 to-orange-400"
                        subtitle={`${formatPerSqft(comp.subject_price_per_sqft)} vs ${formatPerSqft(
                          comp.candidate_price_per_sqft,
                        )}`}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
