import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider } from "../lib/i18n";
import { VerdictCard } from "./VerdictCard";
import { mockVerdict } from "../test/fixtures";

function renderVerdictCard(): void {
  render(
    <LanguageProvider>
      <VerdictCard verdict={mockVerdict} companyName="Acme Corporation" />
    </LanguageProvider>,
  );
}

describe("VerdictCard", () => {
  beforeEach(() => {
    localStorage.setItem("employer-dd-locale", "en");
  });

  it("shows score and score_explanation (UX-01)", () => {
    renderVerdictCard();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(
      screen.getByText("Mixed signals from recent layoffs and steady product shipping."),
    ).toBeInTheDocument();
  });

  it("shows red flags and interesting facts section titles when lists non-empty (UX-02)", () => {
    renderVerdictCard();
    expect(screen.getByRole("heading", { name: /Red flags/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Interesting facts/i })).toBeInTheDocument();
  });

  it.todo("shows evidence section title and https source links (UX-03) — deferred until 06-02");
});
