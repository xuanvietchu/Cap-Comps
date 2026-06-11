import { NextRequest, NextResponse } from "next/server";

type WalkScoreDetails = {
  walkscore: string;
  transitscore: string;
  bikescore: string;
};

function scoreFromAlt(html: string, label: string) {
  const pattern = new RegExp(
    `<img[^>]+alt=["']\\s*(\\d+)\\s+${label}[^"']*["']`,
    "i",
  );
  return html.match(pattern)?.[1] ?? "";
}

export async function POST(request: NextRequest) {
  const body = (await request.json().catch(() => ({}))) as {
    address?: unknown;
  };
  const address = typeof body.address === "string" ? body.address.trim() : "";

  if (!address) {
    return NextResponse.json(
      { error: "Address is required." },
      { status: 400 },
    );
  }

  const walkScoreUrl = `https://www.walkscore.com/score/${encodeURIComponent(
    address,
  )}`;

  const response = await fetch(walkScoreUrl, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    return NextResponse.json(
      { error: `Walk Score returned ${response.status}.` },
      { status: response.status },
    );
  }

  const html = await response.text();
  const scores: WalkScoreDetails = {
    walkscore: scoreFromAlt(html, "Walk Score"),
    transitscore: scoreFromAlt(html, "Transit Score"),
    bikescore: scoreFromAlt(html, "Bike Score"),
  };

  return NextResponse.json(scores);
}
