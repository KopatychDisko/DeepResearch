import type { EventCategory, RunPhase, SourceType, VerdictColor } from "../types";

export const PHASE_STEPS: RunPhase[] = [
  "pending",
  "resolve_identity",
  "awaiting_identity",
  "supervisor",
  "structure_events",
  "merge_timeline",
  "generate_verdict",
  "completed",
];

export const PHASE_LABELS: Record<RunPhase, string> = {
  pending: "Подготовка",
  resolve_identity: "Проверка компании",
  awaiting_identity: "Выбор компании",
  supervisor: "Источники",
  structure_events: "События",
  merge_timeline: "Таймлайн",
  generate_verdict: "Вердикт",
  completed: "Готово",
};

export const SOURCE_LABELS: Record<SourceType, string> = {
  news: "Новости",
  reviews: "Отзывы",
  hh: "HeadHunter",
};

export const CATEGORY_LABELS: Record<EventCategory, string> = {
  funding: "Финансы",
  leadership: "Руководство",
  layoffs: "Сокращения",
  scandal: "Скандал",
  product: "Продукт",
  review_signal: "Отзывы",
};

export const VERDICT_COLOR_LABELS: Record<VerdictColor, string> = {
  green: "Низкий риск",
  yellow: "Смешанные сигналы",
  red: "Высокий риск",
};

export function scoreLabel(score: number): string {
  if (score >= 9) {
    return "Отличный выбор";
  }
  if (score >= 7) {
    return "Скорее позитивно";
  }
  if (score >= 5) {
    return "Нужна проверка";
  }
  if (score >= 3) {
    return "Есть опасения";
  }
  return "Высокий риск";
}
