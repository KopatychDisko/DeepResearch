import type {
  HhVacancyAnalysis,
  HhVacancyAnalysisApi,
  RunStartResponse,
  RunStatusResponse,
  RunViewModel,
} from "./types";

export interface StartRunPayload {
  companyName: string;
  companyUrl: string;
  companyDescription: string;
  responseLanguage: "ru" | "en";
}

async function readError(response: Response): Promise<string> {
  const errorText: string = await response.text();
  if (errorText.length === 0) {
    return `Request failed with status ${response.status}`;
  }
  try {
    const parsed: unknown = JSON.parse(errorText);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "detail" in parsed &&
      typeof (parsed as { detail: unknown }).detail === "string"
    ) {
      return (parsed as { detail: string }).detail;
    }
  } catch {
    // keep raw body
  }
  return errorText;
}

function buildRunRequestBody(payload: StartRunPayload): {
  company_name: string;
  company_url?: string;
  company_description?: string;
  response_language: "ru" | "en";
} {
  const trimmedUrl: string = payload.companyUrl.trim();
  const trimmedDescription: string = payload.companyDescription.trim();
  const body: {
    company_name: string;
    company_url?: string;
    company_description?: string;
    response_language: "ru" | "en";
  } = {
    company_name: payload.companyName.trim(),
    response_language: payload.responseLanguage,
  };
  if (trimmedUrl.length > 0) {
    body.company_url = trimmedUrl;
  }
  if (trimmedDescription.length > 0) {
    body.company_description = trimmedDescription;
  }
  return body;
}

export async function startBackgroundRun(payload: StartRunPayload): Promise<RunStartResponse> {
  const response = await fetch("/runs?background=true", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildRunRequestBody(payload)),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<RunStartResponse>;
}

export async function confirmRunIdentity(runId: string, candidateId: string): Promise<RunStartResponse> {
  const response = await fetch(`/runs/${runId}/identity`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id: candidateId }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<RunStartResponse>;
}

export async function fetchRunStatus(runId: string): Promise<RunStatusResponse> {
  const response = await fetch(`/runs/${runId}`);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<RunStatusResponse>;
}

function mapHhVacancyAnalysis(api: HhVacancyAnalysisApi): HhVacancyAnalysis {
  const status: HhVacancyAnalysis["status"] =
    api.status === "found" ? "found" : "not_found";
  return {
    status,
    employer_name: api.employer_name,
    employer_url: api.employer_profile_url,
    employer_rating: api.employer_rating,
    employer_rating_count: api.employer_rating_count,
    salary_summary: api.salary_summary,
    conditions_summary: api.conditions_summary,
    vacancies: api.vacancies.map((vacancy) => ({
      vacancy_id: vacancy.vacancy_id,
      title: vacancy.title,
      url: vacancy.url,
      salary_text: vacancy.salary_text,
      location_text: vacancy.location_text,
      schedule_text: vacancy.schedule_text,
      published_at: vacancy.published_at,
    })),
  };
}

export function statusToViewModel(status: RunStatusResponse): RunViewModel | null {
  if (status.result === null) {
    return null;
  }
  const viewModel: RunViewModel = {
    runId: status.run_id,
    identity: status.result.identity,
    findings: status.result.findings,
    timeline: status.result.timeline,
    verdict: status.result.verdict,
  };
  if (status.result.hh_vacancy_analysis !== undefined) {
    viewModel.hhVacancyAnalysis = mapHhVacancyAnalysis(status.result.hh_vacancy_analysis);
  }
  return viewModel;
}

export async function resumePollingAfterIdentity(
  runId: string,
  onStatus: (status: RunStatusResponse) => void,
  pollIntervalMs: number,
): Promise<RunViewModel> {
  while (true) {
    const status: RunStatusResponse = await fetchRunStatus(runId);
    onStatus(status);
    if (status.status === "failed") {
      throw new Error(status.error_message ?? "Анализ завершился с ошибкой.");
    }
    if (status.status === "completed") {
      const viewModel: RunViewModel | null = statusToViewModel(status);
      if (viewModel === null) {
        throw new Error("Анализ завершён, но результат отсутствует.");
      }
      return viewModel;
    }
    await new Promise<void>((resolve) => {
      setTimeout(resolve, pollIntervalMs);
    });
  }
}
