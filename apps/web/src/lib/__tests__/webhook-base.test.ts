import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

async function loadWebhookBase() {
  return import("../webhook-base");
}

describe("getWebhookBaseUrl", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("prefers the explicit webhook base over the API base", async () => {
    vi.stubEnv("NEXT_PUBLIC_WEBHOOK_BASE_URL", "https://hooks.quantbridge.app");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.quantbridge.app");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "https://hooks.quantbridge.app",
      isDev: false,
    });
  });

  it("strips trailing slashes from the explicit webhook base", async () => {
    vi.stubEnv("NEXT_PUBLIC_WEBHOOK_BASE_URL", "https://hooks.x.app///");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "https://hooks.x.app",
      isDev: false,
    });
  });

  it("falls back to the API base when the explicit webhook base is whitespace", async () => {
    vi.stubEnv("NEXT_PUBLIC_WEBHOOK_BASE_URL", "   ");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.quantbridge.app");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "https://api.quantbridge.app",
      isDev: false,
    });
  });

  it("falls back to the API base when the explicit webhook base is empty", async () => {
    vi.stubEnv("NEXT_PUBLIC_WEBHOOK_BASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.quantbridge.app");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "https://api.quantbridge.app",
      isDev: false,
    });
  });

  it("marks a localhost API fallback as development", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "http://localhost:8000",
      isDev: true,
    });
  });

  it("marks a loopback IP API fallback as development", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "http://127.0.0.1:8000",
      isDev: true,
    });
  });

  it("marks a remote plain HTTP API fallback as development", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.example.com");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "http://api.example.com",
      isDev: true,
    });
  });

  it("does not mark a remote HTTPS API fallback as development", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.quantbridge.app");

    const { getWebhookBaseUrl } = await loadWebhookBase();

    expect(getWebhookBaseUrl()).toEqual({
      url: "https://api.quantbridge.app",
      isDev: false,
    });
  });

  it("uses getApiBase when neither environment variable is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_WEBHOOK_BASE_URL", undefined);
    vi.stubEnv("NEXT_PUBLIC_API_URL", undefined);

    const { getWebhookBaseUrl } = await loadWebhookBase();
    const { getApiBase } = await import("../api-base");

    expect(getWebhookBaseUrl()).toEqual({
      url: getApiBase(),
      isDev: true,
    });
  });
});
