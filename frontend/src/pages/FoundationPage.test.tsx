import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app/App";

describe("FoundationPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the product foundation and live API version", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: new Headers(),
        json: () =>
          Promise.resolve({
            status: "healthy",
            service: "workflix-api",
            version: "0.1.0",
            environment: "test",
          }),
      }),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /knowledge that moves/i }, { timeout: 10_000 }),
    ).toBeInTheDocument();
    expect(await screen.findByText("API 0.1.0", {}, { timeout: 10_000 })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /api documentation/i })).toHaveAttribute(
      "href",
      "http://localhost:8000/docs",
    );
  });
});
