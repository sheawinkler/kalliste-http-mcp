import { NextResponse } from "next/server";
import { callOrchestrator } from "@/lib/orchestrator";

export async function POST(request: Request) {
  const body = await request.json();
  const data = await callOrchestrator("/memory/write", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return NextResponse.json(data);
}
