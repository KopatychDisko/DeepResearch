import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider } from "../lib/i18n";
import type { EmployerVerdict } from "../types";
import { VerdictCard } from "./VerdictCard";
import { mockVerdict } from "../test/fixtures";

function renderVerdictCard(verdict: EmployerVerdict): void {
  render(
    <LanguageProvider>
      <VerdictCard verdict={verdict} companyName="Acme Corporation" />
    </LanguageProvider>,
  );
}

describe("VerdictCard", () => {
  beforeEach(() => {
    localStorage.setItem("employer-dd-locale", "en");
  });

  it("shows score and score_explanation (UX-01)", () => {
    renderVerdictCard(mockVerdict);
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(
      screen.getByText("Mixed signals from recent layoffs and steady product shipping."),
    ).toBeInTheDocument();
  });

  it("shows red flags and interesting facts section titles when lists non-empty (UX-02)", () => {
    renderVerdictCard(mockVerdict);
    expect(screen.getByRole("heading", { name: /Red flags/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Interesting facts/i })).toBeInTheDocument();
  });

  it("hides evidence until expanded and shows https source links (UX-03)", async () => {
    const user = userEvent.setup();
    renderVerdictCard(mockVerdict);

    expect(
      screen.getByText("Company announced a 10% workforce reduction"),
    ).not.toBeVisible();

    await user.click(screen.getByText(/Verdict evidence \(1\)/));
    expect(
      screen.getByText("Company announced a 10% workforce reduction"),
    ).toBeVisible();
    expect(screen.getByText("Layoffs")).toBeInTheDocument();
    expect(screen.getByText("2024-03-15")).toBeInTheDocument();
    const link: HTMLAnchorElement = screen.getByRole("link", { name: "example.com" });
    expect(link).toHaveAttribute("href", "https://example.com/news/layoffs-2024");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
  });

  it("shows evidence empty copy when expanded and evidence_links is empty (UX-03)", async () => {
    const user = userEvent.setup();
    const emptyEvidence: EmployerVerdict = {
      ...mockVerdict,
      evidence_links: [],
    };
    renderVerdictCard(emptyEvidence);

    await user.click(screen.getByText(/Verdict evidence \(0\)/));
    expect(screen.getByText("No linked sources for this verdict.")).toBeInTheDocument();
  });

  it("omits red flags and interesting facts when lists are empty (SC-2)", () => {
    const noInsights: EmployerVerdict = {
      ...mockVerdict,
      red_flags: [],
      interesting_facts: [],
      risks: [],
    };
    renderVerdictCard(noInsights);
    expect(screen.queryByRole("heading", { name: /Red flags/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Interesting facts/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Risks/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Verdict evidence \(1\)/)).toBeInTheDocument();
  });
});
