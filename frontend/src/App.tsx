import { useRef, useState } from "react";
import {
  confirmRunIdentity,
  fetchRunStatus,
  startBackgroundRun,
} from "./api";
import { CompanySearchForm } from "./components/CompanySearchForm";
import { IdentityPicker } from "./components/IdentityPicker";
import { LanguageToggle } from "./components/LanguageToggle";
import { ResultsDashboard } from "./components/ResultsDashboard";
import { RunProgressCard } from "./components/RunProgressCard";
import { useLanguage } from "./lib/i18n";
import type { RunStatusResponse, RunViewModel } from "./types";

const POLL_INTERVAL_MS = 2000;

export function App() {
  const { locale, t } = useLanguage();
  const [companyName, setCompanyName] = useState<string>("");
  const [companyUrl, setCompanyUrl] = useState<string>("");
  const [companyDescription, setCompanyDescription] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isConfirmingIdentity, setIsConfirmingIdentity] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatusResponse | null>(null);
  const [result, setResult] = useState<RunViewModel | null>(null);
  const activeRunIdRef = useRef<string | null>(null);
  const pollAbortRef = useRef<boolean>(false);

  async function pollUntilComplete(runId: string): Promise<void> {
    pollAbortRef.current = false;
    activeRunIdRef.current = runId;

    while (!pollAbortRef.current) {
      const status: RunStatusResponse = await fetchRunStatus(runId);
      setRunStatus(status);

      if (status.status === "failed") {
        throw new Error(status.error_message ?? t.errorRunFailed);
      }
      if (status.status === "awaiting_input") {
        setIsLoading(false);
        return;
      }
      if (status.status === "completed") {
        if (status.result === null) {
          throw new Error(t.errorNoResult);
        }
        setResult({
          runId: status.run_id,
          identity: status.result.identity,
          findings: status.result.findings,
          timeline: status.result.timeline,
          verdict: status.result.verdict,
        });
        setIsLoading(false);
        return;
      }
      await new Promise<void>((resolve) => {
        setTimeout(resolve, POLL_INTERVAL_MS);
      });
    }
  }

  async function handleSubmit(): Promise<void> {
    const trimmedName: string = companyName.trim();
    if (trimmedName.length < 2) {
      return;
    }
    setIsLoading(true);
    setIsConfirmingIdentity(false);
    setErrorMessage(null);
    setRunStatus(null);
    setResult(null);
    pollAbortRef.current = true;

    try {
      const startedRun = await startBackgroundRun({
        companyName: trimmedName,
        companyUrl: companyUrl.trim(),
        companyDescription: companyDescription.trim(),
        responseLanguage: locale,
      });
      await pollUntilComplete(startedRun.run_id);
    } catch (error: unknown) {
      const message: string =
        error instanceof Error ? error.message : t.errorAnalysisFailed;
      setErrorMessage(message);
      setIsLoading(false);
    }
  }

  async function handleIdentitySelect(candidateId: string): Promise<void> {
    const runId: string | null = activeRunIdRef.current ?? runStatus?.run_id ?? null;
    if (runId === null) {
      setErrorMessage(t.errorNoActiveRun);
      return;
    }
    setIsConfirmingIdentity(true);
    setErrorMessage(null);
    try {
      await confirmRunIdentity(runId, candidateId);
      pollAbortRef.current = false;
      setIsLoading(true);
      await pollUntilComplete(runId);
    } catch (error: unknown) {
      const message: string =
        error instanceof Error ? error.message : t.errorConfirmFailed;
      setErrorMessage(message);
      setIsLoading(false);
    } finally {
      setIsConfirmingIdentity(false);
    }
  }

  const isAwaitingIdentity: boolean = runStatus?.status === "awaiting_input";

  return (
    <main className="app">
      <header className="header">
        <div className="header-top">
          <div className="header-badge">{t.headerBadge}</div>
          <LanguageToggle />
        </div>
        <h1>{t.headerTitle}</h1>
        <p>{t.headerSubtitle}</p>
      </header>

      <CompanySearchForm
        isLoading={isLoading || isConfirmingIdentity}
        companyName={companyName}
        companyUrl={companyUrl}
        companyDescription={companyDescription}
        onCompanyNameChange={setCompanyName}
        onCompanyUrlChange={setCompanyUrl}
        onCompanyDescriptionChange={setCompanyDescription}
        onSubmit={() => {
          void handleSubmit();
        }}
      />

      {errorMessage !== null ? <div className="error-banner">{errorMessage}</div> : null}

      {isLoading || isAwaitingIdentity ? (
        <RunProgressCard status={runStatus} companyName={companyName.trim()} />
      ) : null}

      {isAwaitingIdentity && runStatus !== null && runStatus.identity_candidates.length > 0 ? (
        <IdentityPicker
          candidates={runStatus.identity_candidates}
          message={runStatus.error_message}
          isSubmitting={isConfirmingIdentity}
          onSelect={(candidateId: string) => {
            void handleIdentitySelect(candidateId);
          }}
        />
      ) : null}

      {result !== null ? <ResultsDashboard result={result} /> : null}
    </main>
  );
}
