import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// Allow up to 300s for investigation (Gemini calls + retries)
export const maxDuration = 300;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    console.log(`[invoke] POST to ${BACKEND_URL}/api/investigate`);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 280000); // 280s timeout
    const res = await fetch(`${BACKEND_URL}/api/investigate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!res.ok) {
      const errText = await res.text();
      console.error(`[invoke] Backend error: ${res.status} ${errText}`);
      return NextResponse.json(
        { error: "Investigation failed", detail: errText },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[invoke] Backend unavailable:", error);
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503 }
    );
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const caseId = searchParams.get("case_id");
  const traces = searchParams.get("traces");

  try {
    if (caseId && traces) {
      const res = await fetch(`${BACKEND_URL}/api/cases/${caseId}/traces`);
      if (!res.ok) return NextResponse.json({ traces: [] });
      return NextResponse.json(await res.json());
    }

    const res = await fetch(`${BACKEND_URL}/api/alerts`);
    if (!res.ok) return NextResponse.json({ alerts: [] });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ alerts: [], traces: [] });
  }
}
