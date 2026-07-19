import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageProvider } from "../lib/i18n";
import { ResultsDashboard } from "./ResultsDashboard";
import { mockRunViewModel } from "../test/fixtures";

function renderDashboard(): void {
  render(
    <LanguageProvider>
      <ResultsDashboard result={mockRunViewModel} />
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

  it.todo("shows Timeline tab with timeline.events (UX-05) — deferred until 06-03");
});
