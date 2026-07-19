import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider } from "../lib/i18n";
import type { RunViewModel } from "../types";
import { ResultsDashboard } from "./ResultsDashboard";
import { mockRunViewModel } from "../test/fixtures";

function renderDashboard(result: RunViewModel = mockRunViewModel): void {
  render(
    <LanguageProvider>
      <ResultsDashboard result={result} />
    </LanguageProvider>,
  );
}

describe("ResultsDashboard", () => {
  beforeEach(() => {
    localStorage.setItem("employer-dd-locale", "en");
  });

  it("shows Verdict and Sources tabs; Sources reachable with findings (UX-04)", async () => {
    const user = userEvent.setup();
    renderDashboard();

    expect(screen.getByRole("button", { name: "Verdict" })).toBeInTheDocument();
    const sourcesTab = screen.getByRole("button", { name: /Sources/ });
    expect(sourcesTab).toBeInTheDocument();

    await user.click(sourcesTab);
    expect(screen.getByRole("heading", { name: "Links used in the report" })).toBeInTheDocument();
    expect(screen.getByText("Acme cuts 10% of staff")).toBeInTheDocument();
  });

  it("shows Timeline tab with timeline.events (UX-05)", async () => {
    const user = userEvent.setup();
    renderDashboard();

    const tabs = screen.getAllByRole("button", { name: /Verdict|Timeline|Sources/ });
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      "Verdict",
      "Timeline",
      expect.stringMatching(/^Sources/),
    ]);

    const timelineTab = screen.getByRole("button", { name: "Timeline" });
    await user.click(timelineTab);
    expect(
      screen.getByText("Company announced a 10% workforce reduction"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "example.com" })).toHaveAttribute(
      "href",
      "https://example.com/news/layoffs-2024",
    );
  });

  it("shows timeline empty copy when Timeline tab selected and events empty (UX-05)", async () => {
    const user = userEvent.setup();
    const emptyTimeline: RunViewModel = {
      ...mockRunViewModel,
      timeline: { events: [], conflicts: [] },
    };
    renderDashboard(emptyTimeline);

    await user.click(screen.getByRole("button", { name: "Timeline" }));
    expect(screen.getByText("No events found.")).toBeInTheDocument();
  });
});
