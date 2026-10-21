import { apiFetch } from "@/lib/api-client";
import {
  PythonBacktestBodySchema,
  PythonCapabilitiesSchema,
  PythonRunListSchema,
  PythonRunSchema,
  PythonStrategyListSchema,
  PythonStrategySchema,
  type PythonBacktestBody,
  type PythonStrategyBody,
} from "./schemas";

const BASE = "/api/v1/python-strategies";

export async function getPythonCapabilities(token: string | null) {
  return PythonCapabilitiesSchema.parse(await apiFetch<unknown>(`${BASE}/capabilities`, { token }));
}

export async function listPythonStrategies(token: string | null) {
  return PythonStrategyListSchema.parse(await apiFetch<unknown>(BASE, { token }));
}

export async function savePythonStrategy(
  id: string | null,
  body: PythonStrategyBody,
  token: string | null,
) {
  return PythonStrategySchema.parse(
    await apiFetch<unknown>(id ? `${BASE}/${id}` : BASE, {
      method: id ? "PUT" : "POST",
      body,
      token,
    }),
  );
}

export async function startPythonBacktest(
  id: string,
  body: PythonBacktestBody,
  token: string | null,
) {
  return PythonRunSchema.parse(
    await apiFetch<unknown>(`${BASE}/${id}/backtests`, {
      method: "POST",
      body: PythonBacktestBodySchema.parse(body),
      token,
    }),
  );
}

export async function listPythonRuns(id: string, token: string | null) {
  return PythonRunListSchema.parse(await apiFetch<unknown>(`${BASE}/${id}/backtests`, { token }));
}

export async function getPythonRun(id: string, token: string | null) {
  return PythonRunSchema.parse(await apiFetch<unknown>(`${BASE}/backtests/${id}`, { token }));
}

export async function cancelPythonRun(id: string, token: string | null) {
  return PythonRunSchema.parse(
    await apiFetch<unknown>(`${BASE}/backtests/${id}/cancel`, { method: "POST", token }),
  );
}
