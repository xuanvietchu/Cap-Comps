"use client";

import { useState } from "react";

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

async function geocodeEdmontonAddress(address: string) {
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
  const [submitError, setSubmitError] = useState("");

  function updateField<K extends keyof UiHouseDetails>(
    field: K,
    value: UiHouseDetails[K],
  ) {
    setDetails((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  async function submitForm(e: React.FormEvent) {
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
    <form onSubmit={submitForm} className="flex-1 overflow-y-auto p-8">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold">
            {page === 1 ? "House Details" : "Search Constraints"}
          </h2>

          <p className="text-gray-400">Page {page} of 2</p>
        </div>

        <button
          type="button"
          onClick={onCancel}
          className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-xl"
        >
          Cancel
        </button>
      </div>

      {page === 1 ? (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
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
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 outline-none text-sm"
              >
                {garageOptions.map((option) => (
                  <option key={option.value} value={option.value}>
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
              onChange={(v) => updateField("L_basement1_status", v)}
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
          <div className="mb-6 rounded-xl border border-blue-900 bg-blue-950/40 p-4">
            <h3 className="font-semibold mb-2">Search constraints</h3>

            <p className="text-gray-300">
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

          <div className="grid grid-cols-3 gap-4">
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
        <div className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-300">
          {submitError}
        </div>
      )}

      <div className="flex justify-between mt-8">
        <button
          type="button"
          disabled={page === 1}
          onClick={() => setPage(1)}
          className="bg-gray-800 hover:bg-gray-700 disabled:opacity-40 px-6 py-3 rounded-xl font-semibold"
        >
          Back
        </button>

        <button
          type="submit"
          disabled={isSubmitting}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-xl font-semibold"
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
