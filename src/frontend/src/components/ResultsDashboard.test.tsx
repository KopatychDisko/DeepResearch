import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider } from "../lib/i18n";
import type { RunViewModel } from "../types";
import { ResultsDashboard } from "./ResultsDashboard";
import {
  mockHhNotFoundViewModel,
  mockRunViewModel,
  mockRunViewModelWithHh,
} from "../test/fixtures";

function renderDashboard(result: RunViewModel = mockRunViewModel, contentLocale: "en" | "ru" = "en"): void {
  render(
    <LanguageProvider>
      <ResultsDashboard
        result={result}
        onRetryHhSearch={async () => {}}
        contentLocale={contentLocale}
      />
    </LanguageProvider>,
  );
}

describe("ResultsDashboard", () => {
  beforeEach(() => {
    localStorage.setItem("employer-dd-locale", "en");
  });

  it("hides raw sources until the user expands the section (UX-04)", async () => {
    const user = userEvent.setup();
    renderDashboard();

    expect(screen.getByText("Acme cuts 10% of staff")).not.toBeVisible();

    await user.click(screen.getByText(/Sources \(1\)/));
    expect(screen.getByText("Acme cuts 10% of staff")).toBeVisible();
  });

  it("shows sources empty copy when expanded and findings are empty (UX-04)", async () => {
    const user = userEvent.setup();
    const noFindings: RunViewModel = {
      ...mockRunViewModel,
      findings: [],
    };
    renderDashboard(noFindings);

    await user.click(screen.getByText(/Sources \(0\)/));
    expect(screen.getByText("No sources collected.")).toBeInTheDocument();
  });

  it("shows HH vacancy content when HH section is open by default", () => {
    renderDashboard(mockRunViewModelWithHh);

    expect(screen.getByText("Senior Backend Engineer")).toBeVisible();
  });

  it("shows not_found HH message with company name in HH section", () => {
    renderDashboard(mockHhNotFoundViewModel);

    expect(
      screen.getByText('Employer not found on hh.ru for "Acme Corporation".'),
    ).toBeVisible();
  });

  it("omits HH section for legacy runs without hhVacancyAnalysis", () => {
    renderDashboard(mockRunViewModel);

    expect(screen.queryByText(/HH vacancies/)).not.toBeInTheDocument();
  });

  it("keeps verdict score unchanged when HH data is present", () => {
    renderDashboard(mockRunViewModelWithHh);

    expect(screen.getByText("6")).toBeInTheDocument();
    expect(
      screen.getByText("Mixed signals from recent layoffs and steady product shipping."),
    ).toBeInTheDocument();
  });
});
