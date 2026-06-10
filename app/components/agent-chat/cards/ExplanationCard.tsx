import {
  ExplanationFeature,
  ExplanationPayload,
  ExplanationSection,
} from "../types";

function FeatureBucket({
  label,
  features,
}: {
  label: string;
  features: ExplanationFeature[];
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
        {label}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {features.length ? (
          features.map((feature) => (
            <span
              key={`${feature.feature}-${feature.value}-${feature.direction}`}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200"
            >
              {feature.feature} = {feature.value} (
              {feature.approx_pct_effect.toFixed(1)}
              %)
            </span>
          ))
        ) : (
          <span className="text-xs text-slate-500">No features returned</span>
        )}
      </div>
    </div>
  );
}

export default function ExplanationCard({
  explanation,
}: {
  explanation: ExplanationPayload;
}) {
  const price = explanation.price;
  const comps = null as ExplanationSection | null;

  return (
    <div className="max-w-4xl rounded-2xl border border-white/10 bg-[#111827] p-5 text-slate-50">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Explanation
          </p>
          <h3 className="mt-2 text-lg font-semibold text-white">
            Model interpretation
          </h3>
        </div>
      </div>

      {price && (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
              SHAP price drivers
            </p>
          </div>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <FeatureBucket
              label="Pushes up"
              features={price.top_positive ?? []}
            />
            <FeatureBucket
              label="Pushes down"
              features={price.top_negative ?? []}
            />
          </div>
        </div>
      )}

      {comps && (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
              Comps context
            </p>
            <p className="text-xs text-slate-400">
              Top {comps.top_comp_count ?? 0} comps
            </p>
          </div>
          {comps.top_comp ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">
                Top comp: {comps.top_comp.address}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">
                Score: {(comps.top_comp.similarity_score * 100).toFixed(1)}%
              </span>
            </div>
          ) : null}
          {comps.top_comps?.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {comps.top_comps.slice(0, 3).map((comp) => (
                <span
                  key={comp.address}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200"
                >
                  {comp.address} · {(comp.similarity_score * 100).toFixed(1)}%
                </span>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
