export type HouseDetails = {
  address: string;
  assessmentClass: string;
  zoning: string;
  bathroomsCount: string;
  bedroomsCount: string;
  livingArea: string;
  lotSizeArea: string;
  yearBuilt: string;
  garage: string;
  houseStyle: string;
  basement: string;
  neighbourhoodName: string;
  lat: string;
  lon: string;
  L_basement2_status: string;
  walkscore: string;
  transitscore: string;
  bikescore: string;
  L_basement1_size: string;
  L_basement1_status: string;

  exteriorWood: string;
  exteriorBrick: string;
  exteriorVinyl: string;
  exteriorStone: string;
  exteriorOther: string;
  exteriorMetal: string;
  exteriorStucco: string;
  exteriorConcrete: string;

  floorCeramic_Tile: string;
  floorLaminate_Flooring: string;
  floorLinoleum: string;
  floorHardwood: string;
  floorCarpet: string;

  foundationConcrete_Perimeter: string;
  foundationOther: string;

  "heatForced_Air-1": string;
  heatOther: string;
  heatNatural_Gas: string;

  roofAsphalt_Shingles: string;
  roofOther: string;

  extraGarage_Control: string;
  extraOther: string;
  "extraAir_Conditioning-Central": string;
  "extraDishwasher-Built-In": string;
  extraMicrowave_Hood_Fan: string;
  "extraStove-Electric": string;
  extraGarage_Opener: string;
  extraRefrigerator: string;
  extraWindow_Coverings: string;
  extraHood_Fan: string;
  extraWasher: string;
  extraDryer: string;

  maxDistanceKm: string;
  sqftTolerancePct: string;
  yearTolerance: string;
};

export type UiHouseDetails = {
  address: string;
  assessmentClass: "" | "residential" | "condo";
  zoning: string;
  bathroomsCount: string;
  bedroomsCount: string;
  livingArea: string;
  lotSizeArea: string;
  yearBuilt: string;
  garage: string;
  houseStyle: string;
  basement: string;
  neighbourhoodName: string;
  lat: string;
  lon: string;
  L_basement2_status: string;
  L_basement1_size: string;
  L_basement1_status: string;

  exterior: string[];
  floor: string[];
  foundation: string[];
  heat: string[];
  roof: string[];
  extra: string[];

  walkscore: string;
  transitscore: string;
  bikescore: string;

  maxDistanceKm: string;
  sqftTolerancePct: string;
  yearTolerance: string;
};

export const initialUiDetails: UiHouseDetails = {
  address: "12224 55 STREET NW",
  assessmentClass: "residential",
  zoning: "RF1",
  bathroomsCount: "2.0",
  bedroomsCount: "3.0",
  livingArea: "1143.0",
  lotSizeArea: "548.0",
  yearBuilt: "1958.0",
  garage: "1",
  houseStyle: "bungalow",
  basement: "",
  neighbourhoodName: "Newton",
  lat: "",
  lon: "",
  L_basement2_status: "Fully Finished",
  L_basement1_size: "Full",
  L_basement1_status: "Finished",

  walkscore: "",
  transitscore: "",
  bikescore: "",

  exterior: ["Stucco", "Concrete"],
  floor: ["Linoleum", "Carpet"],
  foundation: ["Concrete Perimeter"],
  heat: ["Forced Air", "Natural Gas"],
  roof: ["Asphalt Shingles"],
  extra: [
    "Other",
    "Stove-Electric",
    "Refrigerator",
    "Window Coverings",
    "Washer",
    "Dryer",
  ],

  maxDistanceKm: "3",
  sqftTolerancePct: "20",
  yearTolerance: "10",
};

export const blankUiDetails: UiHouseDetails = {
  address: "",
  assessmentClass: "",
  zoning: "",
  bathroomsCount: "",
  bedroomsCount: "",
  livingArea: "",
  lotSizeArea: "",
  yearBuilt: "",
  garage: "",
  houseStyle: "",
  basement: "",
  neighbourhoodName: "",
  lat: "",
  lon: "",
  L_basement2_status: "",
  L_basement1_size: "",
  L_basement1_status: "",

  walkscore: "",
  transitscore: "",
  bikescore: "",

  exterior: [],
  floor: [],
  foundation: [],
  heat: [],
  roof: [],
  extra: [],

  maxDistanceKm: initialUiDetails.maxDistanceKm,
  sqftTolerancePct: initialUiDetails.sqftTolerancePct,
  yearTolerance: initialUiDetails.yearTolerance,
};

export function toBackendDetails(ui: UiHouseDetails): HouseDetails {
  return {
    address: ui.address,
    assessmentClass: ui.assessmentClass,
    zoning: ui.zoning,
    bathroomsCount: ui.bathroomsCount,
    bedroomsCount: ui.bedroomsCount,
    livingArea: ui.livingArea,
    lotSizeArea: ui.lotSizeArea,
    yearBuilt: ui.yearBuilt,
    garage: ui.garage,
    houseStyle: ui.houseStyle,
    basement: ui.basement,
    neighbourhoodName: ui.neighbourhoodName,

    lat: ui.lat,
    lon: ui.lon,
    walkscore: ui.walkscore,
    transitscore: ui.transitscore,
    bikescore: ui.bikescore,

    L_basement2_status: ui.L_basement2_status,
    L_basement1_size: ui.L_basement1_size,
    L_basement1_status: ui.L_basement1_status,

    exteriorWood: ui.exterior.includes("Wood") ? "1" : "0",
    exteriorBrick: ui.exterior.includes("Brick") ? "1" : "0",
    exteriorVinyl: ui.exterior.includes("Vinyl") ? "1" : "0",
    exteriorStone: ui.exterior.includes("Stone") ? "1" : "0",
    exteriorOther: ui.exterior.includes("Other") ? "1" : "0",
    exteriorMetal: ui.exterior.includes("Metal") ? "1" : "0",
    exteriorStucco: ui.exterior.includes("Stucco") ? "1" : "0",
    exteriorConcrete: ui.exterior.includes("Concrete") ? "1" : "0",

    floorCeramic_Tile: ui.floor.includes("Ceramic Tile") ? "1" : "0",
    floorLaminate_Flooring: ui.floor.includes("Laminate Flooring") ? "1" : "0",
    floorLinoleum: ui.floor.includes("Linoleum") ? "1" : "0",
    floorHardwood: ui.floor.includes("Hardwood") ? "1" : "0",
    floorCarpet: ui.floor.includes("Carpet") ? "1" : "0",

    foundationConcrete_Perimeter: ui.foundation.includes("Concrete Perimeter")
      ? "1"
      : "0",
    foundationOther: ui.foundation.includes("Other") ? "1" : "0",

    "heatForced_Air-1": ui.heat.includes("Forced Air") ? "1" : "0",
    heatOther: ui.heat.includes("Other") ? "1" : "0",
    heatNatural_Gas: ui.heat.includes("Natural Gas") ? "1" : "0",

    roofAsphalt_Shingles: ui.roof.includes("Asphalt Shingles") ? "1" : "0",
    roofOther: ui.roof.includes("Other") ? "1" : "0",

    extraGarage_Control: ui.extra.includes("Garage Control") ? "1" : "0",
    extraOther: ui.extra.includes("Other") ? "1" : "0",
    "extraAir_Conditioning-Central": ui.extra.includes(
      "Air Conditioning-Central",
    )
      ? "1"
      : "0",
    "extraDishwasher-Built-In": ui.extra.includes("Dishwasher-Built-In")
      ? "1"
      : "0",
    extraMicrowave_Hood_Fan: ui.extra.includes("Microwave Hood Fan")
      ? "1"
      : "0",
    "extraStove-Electric": ui.extra.includes("Stove-Electric") ? "1" : "0",
    extraGarage_Opener: ui.extra.includes("Garage Opener") ? "1" : "0",
    extraRefrigerator: ui.extra.includes("Refrigerator") ? "1" : "0",
    extraWindow_Coverings: ui.extra.includes("Window Coverings") ? "1" : "0",
    extraHood_Fan: ui.extra.includes("Hood Fan") ? "1" : "0",
    extraWasher: ui.extra.includes("Washer") ? "1" : "0",
    extraDryer: ui.extra.includes("Dryer") ? "1" : "0",

    maxDistanceKm: ui.maxDistanceKm,
    sqftTolerancePct: ui.sqftTolerancePct,
    yearTolerance: ui.yearTolerance,
  };
}

export function toUiDetails(details: HouseDetails): UiHouseDetails {
  return {
    address: details.address ?? "",
    assessmentClass:
      details.assessmentClass === "condo"
        ? "condo"
        : details.assessmentClass === "residential"
          ? "residential"
          : "",
    zoning: details.zoning,
    bathroomsCount: details.bathroomsCount,
    bedroomsCount: details.bedroomsCount,
    livingArea: details.livingArea,
    lotSizeArea: details.lotSizeArea,
    yearBuilt: details.yearBuilt,
    garage: details.garage,
    houseStyle: details.houseStyle,
    basement: details.basement,
    neighbourhoodName: details.neighbourhoodName,
    lat: details.lat,
    lon: details.lon,
    L_basement2_status: details.L_basement2_status,
    L_basement1_size: details.L_basement1_size,
    L_basement1_status: details.L_basement1_status,

    walkscore: details.walkscore,
    transitscore: details.transitscore,
    bikescore: details.bikescore,

    exterior: [
      details.exteriorWood === "1" && "Wood",
      details.exteriorBrick === "1" && "Brick",
      details.exteriorVinyl === "1" && "Vinyl",
      details.exteriorStone === "1" && "Stone",
      details.exteriorOther === "1" && "Other",
      details.exteriorMetal === "1" && "Metal",
      details.exteriorStucco === "1" && "Stucco",
      details.exteriorConcrete === "1" && "Concrete",
    ].filter(Boolean) as string[],

    floor: [
      details.floorCeramic_Tile === "1" && "Ceramic Tile",
      details.floorLaminate_Flooring === "1" && "Laminate Flooring",
      details.floorLinoleum === "1" && "Linoleum",
      details.floorHardwood === "1" && "Hardwood",
      details.floorCarpet === "1" && "Carpet",
    ].filter(Boolean) as string[],

    foundation: [
      details.foundationConcrete_Perimeter === "1" && "Concrete Perimeter",
      details.foundationOther === "1" && "Other",
    ].filter(Boolean) as string[],

    heat: [
      details["heatForced_Air-1"] === "1" && "Forced Air",
      details.heatOther === "1" && "Other",
      details.heatNatural_Gas === "1" && "Natural Gas",
    ].filter(Boolean) as string[],

    roof: [
      details.roofAsphalt_Shingles === "1" && "Asphalt Shingles",
      details.roofOther === "1" && "Other",
    ].filter(Boolean) as string[],

    extra: [
      details.extraGarage_Control === "1" && "Garage Control",
      details.extraOther === "1" && "Other",
      details["extraAir_Conditioning-Central"] === "1" &&
        "Air Conditioning-Central",
      details["extraDishwasher-Built-In"] === "1" && "Dishwasher-Built-In",
      details.extraMicrowave_Hood_Fan === "1" && "Microwave Hood Fan",
      details["extraStove-Electric"] === "1" && "Stove-Electric",
      details.extraGarage_Opener === "1" && "Garage Opener",
      details.extraRefrigerator === "1" && "Refrigerator",
      details.extraWindow_Coverings === "1" && "Window Coverings",
      details.extraHood_Fan === "1" && "Hood Fan",
      details.extraWasher === "1" && "Washer",
      details.extraDryer === "1" && "Dryer",
    ].filter(Boolean) as string[],

    maxDistanceKm: details.maxDistanceKm,
    sqftTolerancePct: details.sqftTolerancePct,
    yearTolerance: details.yearTolerance,
  };
}
