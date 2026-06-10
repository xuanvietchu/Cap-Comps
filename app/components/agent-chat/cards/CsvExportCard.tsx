import { CsvExportPayload } from "../types";

export default function CsvExportCard({ exportCsv }: { exportCsv: CsvExportPayload }) {
  const missingCount = exportCsv.missing_addresses?.length ?? 0;

  return (
    <div className="max-w-2xl rounded-2xl border border-emerald-400/20 bg-emerald-400/5 p-5 text-slate-50">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-emerald-200/80">
            CSV export
          </p>
          <h3 className="mt-2 text-lg font-semibold text-white">
            {exportCsv.filename}
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            {exportCsv.row_count} row{exportCsv.row_count === 1 ? "" : "s"}
            {missingCount ? `, ${missingCount} address not found` : ""}
          </p>
        </div>

        {exportCsv.data_url ? (
          <a
            href={exportCsv.data_url}
            download={exportCsv.filename}
            className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-slate-100"
          >
            Download CSV
          </a>
        ) : null}
      </div>
    </div>
  );
}
