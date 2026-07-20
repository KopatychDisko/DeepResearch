import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider } from "../lib/i18n";
import {
  mockHhVacancyAnalysisFound,
  mockHhVacancyAnalysisNotFound,
} from "../test/fixtures";
import { HhVacanciesPanel } from "./HhVacanciesPanel";

function renderPanel(
  hhVacancyAnalysis: typeof mockHhVacancyAnalysisFound,
  companyName: string,
): void {
  render(
    <LanguageProvider>
      <details open>
        <summary>HH vacancies</summary>
        <HhVacanciesPanel
          hhVacancyAnalysis={hhVacancyAnalysis}
          companyName={companyName}
        />
      </details>
    </LanguageProvider>,
  );
}

describe("HhVacanciesPanel", () => {
  beforeEach(() => {
    localStorage.setItem("employer-dd-locale", "en");
  });

  it("shows not_found message with company name when expanded", () => {
    renderPanel(mockHhVacancyAnalysisNotFound, "Acme Corporation");

    expect(
      screen.getByText('Employer not found on hh.ru for "Acme Corporation".'),
    ).toBeInTheDocument();
  });

  it("shows vacancy titles and correct link href when found", () => {
    renderPanel(mockHhVacancyAnalysisFound, "Acme Corporation");

    const backendLink = screen.getByRole("link", { name: /Senior Backend Engineer/i });
    expect(backendLink).toHaveAttribute("href", "https://hh.ru/vacancy/100001");
    expect(screen.getByText("Product Manager")).toBeInTheDocument();
    expect(screen.getByText("150 000 – 220 000 ₽ typical range for engineering roles.")).toBeInTheDocument();
  });

  it("hides panel content when parent details is closed", () => {
    render(
      <LanguageProvider>
        <details>
          <summary>HH vacancies</summary>
          <HhVacanciesPanel
            hhVacancyAnalysis={mockHhVacancyAnalysisFound}
            companyName="Acme Corporation"
          />
        </details>
      </LanguageProvider>,
    );

    expect(screen.getByText("Senior Backend Engineer")).not.toBeVisible();
  });
});
