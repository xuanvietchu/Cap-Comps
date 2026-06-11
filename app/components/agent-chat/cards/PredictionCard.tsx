import { PredictionBand } from "../types";
import { formatCurrency } from "../utils";

export default function PredictionCard({
  prediction,
}: {
  prediction: PredictionBand;
}) {
  const confidenceLabel =
    prediction.interval_width_ratio < 0.1
      ? "High"
      : prediction.interval_width_ratio < 0.3
        ? "Medium"
        : "Low";

  return (
    <div className="max-w-2xl rounded-2xl border border-white/10 bg-[#111827] p-5 text-slate-50">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Prediction
          </p>
          <h3 className="mt-2 text-3xl font-semibold">
            {formatCurrency(prediction.predicted_price)}
          </h3>
          <p className="mt-2 text-sm text-slate-400">
            Range {formatCurrency(prediction.predicted_price_low)} to{" "}
            {formatCurrency(prediction.predicted_price_high)}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
            Confidence
          </p>
          <p className="mt-1 text-lg font-semibold capitalize text-white">
            {confidenceLabel}
          </p>
        </div>
      </div>
    </div>
  );
}
