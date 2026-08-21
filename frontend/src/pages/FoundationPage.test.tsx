import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../app/App";

describe("Workflix authentication", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("renders the login experience and demo account controls", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: /acesse sua conta/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /colaborador/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /administrador/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("employee@workflix.demo")).toBeInTheDocument();
  });
});
