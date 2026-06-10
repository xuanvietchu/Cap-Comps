import { HouseDetails } from "../houseDetails";

export type PredictionBand = {
  predicted_price: number;
  predicted_price_low: number;
  predicted_price_high: number;
  confidence_level: "high" | "medium" | "low" | string;
  interval_width: number;
  interval_width_ratio: number;
};

export type Comp = {
  address: string;
  sold_price: number;
  sold_date: string;
  distance_km?: number | null;
  similarity_score: number;
  leaf_similarity_score?: number | null;
  price_per_sqft_similarity?: number | null;
  leaf_matches?: number | null;
  leaf_count?: number | null;
  subject_price_per_sqft?: number | null;
  candidate_price_per_sqft?: number | null;
  predicted_value?: number | null;
  yearBuilt?: number | null;
};

export type ExplanationFeature = {
  feature: string;
  value: string;
  shap_log_effect: number;
  approx_pct_effect: number;
  direction: "up" | "down" | "neutral";
};

export type ExplanationSection = {
  kind: string;
  summary?: string;
  predicted_price?: number | null;
  top_positive?: ExplanationFeature[];
  top_negative?: ExplanationFeature[];
  feature_count?: number;
  top_comp?: Comp | null;
  top_comp_count?: number;
  top_comps?: Comp[];
};

export type ExplanationPayload = {
  price?: ExplanationSection | null;
  comps?: ExplanationSection | null;
};

export type IntentAnalysis = {
  intent?: string;
  confidence?: string;
  summary?: string;
  planned_tools?: string[];
};

export type DisplayOptions = {
  show_prediction?: boolean;
  show_comps?: boolean;
  show_csv_export?: boolean;
};

export type CsvExportPayload = {
  status: "ready" | "error" | string;
  filename: string;
  row_count: number;
  requested_addresses: string[];
  missing_addresses: string[];
  data_url?: string | null;
};

export type AgentTraceEvent = {
  step: string;
  detail: string;
  payload?: unknown;
};

export type Message = {
  id: string;
  role: "user" | "agent";
  content: string;
  comps?: Comp[];
  prediction?: PredictionBand | null;
  confidence_level?: string;
  intent?: string;
  explanation?: ExplanationPayload | null;
  display?: DisplayOptions;
  intent_analysis?: IntentAnalysis | null;
  agent_trace?: AgentTraceEvent[];
  export_csv?: CsvExportPayload | null;
  isStreaming?: boolean;
};

export type Conversation = {
  id: string;
  title: string;
  houseDetails: HouseDetails;
  messages: Message[];
};
