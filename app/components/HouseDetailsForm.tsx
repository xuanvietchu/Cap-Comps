"use client";

import { useRef, useState, type ChangeEvent, type FormEvent } from "react";

import {
  HouseDetails,
  UiHouseDetails,
  initialUiDetails,
  toUiDetails,
  toBackendDetails,
} from "./houseDetails";
import {
  assessmentClassOptions,
  garageOptions,
  houseStyleOptions,
  basementOptions,
  basementSizeOptions,
  basementStatusOptions,
  basement2StatusOptions,
  exteriorOptions,
  floorOptions,
  foundationOptions,
  heatOptions,
  roofOptions,
  extraOptions,
  zoningOptions,
  neighbourhoodOptions,
} from "./houseDetailOptions";

import {
  TextInput,
  NumberInput,
  SelectInput,
  MultiSelectField,
  SearchableInput,
} from "./houseFormFields";

type ParsedHouseDetailsResponse = {
  details?: Partial<UiHouseDetails>;
  summary?: string;
};

async function geocodeEdmontonAddress(address: string) {
  // Coordinates anchor distance-based comp filtering, so keep geocoding Edmonton-scoped.
  const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=5&q=${encodeURIComponent(
    address,
  )}`;

  const response = await fetch(url, {
    headers: {
      "Accept-Language": "en",
    },
  });

  const data = await response.json();

  console.log("Coordinates: ", data);

  if (!Array.isArray(data) || data.length === 0) {
    throw new Error("Address not found.");
  }

  const match = data.find((place) => {
    const addressDetails = place.address ?? {};
    const city =
      addressDetails.city ??
      addressDetails.town ??
      addressDetails.municipality ??
      "";

    return city.toLowerCase() === "edmonton";
  });

  if (!match) {
    throw new Error(
      "We do not support addresses outside Edmonton. Choose another one or modify your address.",
    );
  }

  return {
    formattedAddress: address,
    lat: String(match.lat),
    lon: String(match.lon),
  };
}

function fileToBase64(file: File) {
  // FastAPI receives PDFs as JSON, so the browser strips the data URL prefix.
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    };
    reader.onerror = () => reject(new Error("Could not read the PDF file."));
    reader.readAsDataURL(file);
  });
}

function backendUrl(path: string) {
  // Allow deployed demos to point at a hosted API without changing component code.
  const configuredUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configuredUrl) {
    return `${configuredUrl.replace(/\/$/, "")}${path}`;
  }

  const host =
    typeof window === "undefined" || !window.location.hostname
      ? "localhost"
      : window.location.hostname;
  return `http://${host}:8000${path}`;
}

export default function HouseDetailsForm({
  initialDetails,
  onSubmit,
  onCancel,
}: {
  initialDetails?: HouseDetails;
  onSubmit: (details: HouseDetails) => void;
  onCancel: () => void;
}) {
  const [page, setPage] = useState(1);
  const [details, setDetails] = useState<UiHouseDetails>(
    initialDetails ? toUiDetails(initialDetails) : initialUiDetails,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isParsingPdf, setIsParsingPdf] = useState(false);
  const [isPdfModalOpen, setIsPdfModalOpen] = useState(false);
  const [selectedPdfFile, setSelectedPdfFile] = useState<File | null>(null);
  const [submitError, setSubmitError] = useState("");
  const [pdfError, setPdfError] = useState("");
  const [pdfMessage, setPdfMessage] = useState("");
  const pdfInputRef = useRef<HTMLInputElement | null>(null);

  function updateField<K extends keyof UiHouseDetails>(
    field: K,
    value: UiHouseDetails[K],
  ) {
    setDetails((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  function handlePdfFileSelection(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    setSubmitError("");
    setPdfMessage("");
    setPdfError("");

    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setPdfError("Upload a PDF file.");
      return;
    }

    setSelectedPdfFile(file);
  }

  async function confirmPdfUpload() {
    // Ask the backend to map PDF labels into the exact fields used by page one.
    if (!selectedPdfFile) {
      setPdfError("Choose a PDF file first.");
      return;
    }

    setSubmitError("");
    setPdfMessage("");
    setPdfError("");

    try {
      setIsParsingPdf(true);
      const dataBase64 = await fileToBase64(selectedPdfFile);
      const response = await fetch(backendUrl("/parse-house-pdf"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: selectedPdfFile.name,
          mime_type: selectedPdfFile.type || "application/pdf",
          data_base64: dataBase64,
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const parsed = (await response.json()) as ParsedHouseDetailsResponse;
      const parsedDetails = parsed.details ?? {};
      const foundFields = Object.keys(parsedDetails).filter(
        (key) => parsedDetails[key as keyof UiHouseDetails] !== undefined,
      );

      if (foundFields.length === 0) {
        setPdfMessage("No house detail fields were found in the PDF.");
        return;
      }

      setDetails((prev) => ({
        ...prev,
        ...parsedDetails,
      }));
      setPdfMessage(
        `Filled ${foundFields.length} fields on the first page of the form.`,
      );
      setSelectedPdfFile(null);
      setIsPdfModalOpen(false);
    } catch (error) {
      setPdfError(
        error instanceof TypeError
          ? "Could not reach the backend at port 8000. Make sure FastAPI is running, then try again."
          : error instanceof Error
            ? error.message
            : "Could not parse the PDF.",
      );
    } finally {
      setIsParsingPdf(false);
    }
  }

  async function submitForm(e: FormEvent) {
    e.preventDefault();
    setSubmitError("");

    if (page === 1) {
      setPage(2);
      return;
    }

    try {
      setIsSubmitting(true);

      const geo = await geocodeEdmontonAddress(details.address);

      const backendDetails = {
        ...toBackendDetails({
          ...details,
          address: geo.formattedAddress,
        }),
        lat: geo.lat,
        lon: geo.lon,
      };

      onSubmit(backendDetails);
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Could not validate this address.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submitForm}
      className="flex-1 overflow-y-auto bg-slate-950/60 p-6 sm:p-8"
    >
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">
            {page === 1 ? "House Details" : "Search Constraints"}
          </h2>

          <p className="text-slate-400">Page {page} of 2</p>
        </div>

        <div className="flex items-center gap-2">
          <input
            ref={pdfInputRef}
            type="file"
            accept="application/pdf"
            onChange={handlePdfFileSelection}
            className="hidden"
          />

          <button
            type="button"
            title="Upload PDF"
            aria-label="Upload PDF"
            disabled={isParsingPdf}
            onClick={() => {
              setPdfError("");
              setPdfMessage("");
              setSelectedPdfFile(null);
              setIsPdfModalOpen(true);
            }}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isParsingPdf ? (
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-amber-300" />
            ) : (
              <svg
                aria-hidden="true"
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <path d="M17 8 12 3 7 8" />
                <path d="M12 3v12" />
              </svg>
            )}
          </button>

          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:bg-white/10"
          >
            Cancel
          </button>
        </div>
      </div>

      {isPdfModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Upload property PDF
                </h3>
                <p className="mt-1 text-sm text-slate-400">
                  The whole PDF will be used to fill the first page of the form.
                </p>
              </div>

              <button
                type="button"
                aria-label="Close PDF upload"
                disabled={isParsingPdf}
                onClick={() => {
                  setIsPdfModalOpen(false);
                  setPdfError("");
                  setSelectedPdfFile(null);
                }}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-300 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                X
              </button>
            </div>

            <button
              type="button"
              disabled={isParsingPdf}
              onClick={() => pdfInputRef.current?.click()}
              className="mt-5 flex min-h-32 w-full flex-col items-center justify-center rounded-2xl border border-dashed border-white/20 bg-white/5 px-4 py-6 text-center transition hover:bg-white/8 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <svg
                aria-hidden="true"
                className="h-7 w-7 text-amber-200"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <path d="M17 8 12 3 7 8" />
                <path d="M12 3v12" />
              </svg>
              <span className="mt-3 text-sm font-medium text-slate-100">
                {selectedPdfFile ? selectedPdfFile.name : "Choose a PDF file"}
              </span>
              {selectedPdfFile && (
                <span className="mt-1 text-xs text-slate-500">
                  {(selectedPdfFile.size / 1024 / 1024).toFixed(2)} MB
                </span>
              )}
            </button>

            {pdfError && (
              <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-200">
                {pdfError}
              </div>
            )}

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={isParsingPdf}
                onClick={() => {
                  setIsPdfModalOpen(false);
                  setPdfError("");
                  setSelectedPdfFile(null);
                }}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={isParsingPdf || !selectedPdfFile}
                onClick={confirmPdfUpload}
                className="rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isParsingPdf ? "Parsing..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {page === 1 ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            <TextInput
              label="address"
              value={details.address}
              onChange={(v) => updateField("address", v)}
            />

            <SelectInput
              label="assessmentClass"
              value={details.assessmentClass}
              options={assessmentClassOptions}
              onChange={(v) =>
                updateField(
                  "assessmentClass",
                  v as UiHouseDetails["assessmentClass"],
                )
              }
            />

            <SearchableInput
              label="zoning"
              value={details.zoning}
              options={zoningOptions}
              onChange={(v) => updateField("zoning", v)}
            />

            <NumberInput
              label="bathroomsCount"
              value={details.bathroomsCount}
              onChange={(v) => updateField("bathroomsCount", v)}
            />

            <NumberInput
              label="bedroomsCount"
              value={details.bedroomsCount}
              onChange={(v) => updateField("bedroomsCount", v)}
            />

            <NumberInput
              label="livingArea"
              value={details.livingArea}
              onChange={(v) => updateField("livingArea", v)}
            />

            <NumberInput
              label="lotSizeArea"
              value={details.lotSizeArea}
              onChange={(v) => updateField("lotSizeArea", v)}
            />

            <NumberInput
              label="yearBuilt"
              value={details.yearBuilt}
              onChange={(v) => updateField("yearBuilt", v)}
            />

            <label className="block">
              <span className="block text-xs text-gray-300 mb-1">Garage</span>

              <select
                value={details.garage}
                onChange={(e) => updateField("garage", e.target.value)}
                className="w-full rounded-xl border border-gray-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none"
              >
                {garageOptions.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    className="bg-slate-800 text-white"
                  >
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <SelectInput
              label="houseStyle"
              value={details.houseStyle}
              options={houseStyleOptions}
              onChange={(v) => updateField("houseStyle", v)}
            />

            <SelectInput
              label="basement"
              value={details.basement}
              options={basementOptions}
              onChange={(v) => updateField("basement", v)}
            />

            <SearchableInput
              label="neighbourhoodName"
              value={details.neighbourhoodName}
              options={neighbourhoodOptions}
              onChange={(v) => updateField("neighbourhoodName", v)}
            />
            <SelectInput
              label="basement1_size"
              value={details.L_basement1_size}
              options={basementSizeOptions}
              onChange={(v) => updateField("L_basement1_size", v)}
            />

            <SelectInput
              label="basement1_status"
              value={details.L_basement1_status}
              options={basementStatusOptions}
              onChange={(v) => updateField("L_basement1_status", v)}
            />

            <SelectInput
              label="basement2_status"
              value={details.L_basement2_status}
              options={basement2StatusOptions}
              onChange={(v) => updateField("L_basement2_status", v)}
            />
          </div>

          <MultiSelectField
            label="Exterior"
            values={exteriorOptions}
            selected={details.exterior}
            onChange={(v) => updateField("exterior", v)}
          />

          <MultiSelectField
            label="Floor"
            values={floorOptions}
            selected={details.floor}
            onChange={(v) => updateField("floor", v)}
          />

          <MultiSelectField
            label="Foundation"
            values={foundationOptions}
            selected={details.foundation}
            onChange={(v) => updateField("foundation", v)}
          />

          <MultiSelectField
            label="Heat"
            values={heatOptions}
            selected={details.heat}
            onChange={(v) => updateField("heat", v)}
          />

          <MultiSelectField
            label="Roof"
            values={roofOptions}
            selected={details.roof}
            onChange={(v) => updateField("roof", v)}
          />

          <MultiSelectField
            label="Extra"
            values={extraOptions}
            selected={details.extra}
            onChange={(v) => updateField("extra", v)}
          />
        </div>
      ) : (
        <div>
          <div className="mb-6 rounded-2xl border border-amber-400/15 bg-amber-400/8 p-4">
            <h3 className="mb-2 font-semibold text-white">Search constraints</h3>

            <p className="text-slate-300">
              The agent will search for homes within about{" "}
              <span className="font-semibold text-white">
                {details.maxDistanceKm} kilometers
              </span>
              , within{" "}
              <span className="font-semibold text-white">
                {details.sqftTolerancePct}%
              </span>{" "}
              on square footage, and within{" "}
              <span className="font-semibold text-white">
                {details.yearTolerance} years
              </span>{" "}
              on age.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <NumberInput
              label="maxDistanceKm"
              value={details.maxDistanceKm}
              onChange={(v) => updateField("maxDistanceKm", v)}
            />

            <NumberInput
              label="sqftTolerancePct"
              value={details.sqftTolerancePct}
              onChange={(v) => updateField("sqftTolerancePct", v)}
            />

            <NumberInput
              label="yearTolerance"
              value={details.yearTolerance}
              onChange={(v) => updateField("yearTolerance", v)}
            />
          </div>
        </div>
      )}
      {submitError && (
        <div className="mt-6 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-red-200">
          {submitError}
        </div>
      )}
      {pdfMessage && (
        <div className="mt-6 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-emerald-100">
          {pdfMessage}
        </div>
      )}

      <div className="flex justify-between mt-8">
        <button
          type="button"
          disabled={page === 1}
          onClick={() => setPage(1)}
          className="rounded-xl border border-white/10 bg-white/5 px-6 py-3 font-semibold text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Back
        </button>

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-6 py-3 font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting
            ? "Checking address..."
            : page === 1
              ? "Next"
              : "Confirm"}
        </button>
      </div>
    </form>
  );
}
