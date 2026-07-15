import { CATEGORY_LABELS } from "../lib/labels";
import type { CanonicalTimeline } from "../types";

interface TimelineViewProps {
  timeline: CanonicalTimeline;
}

export function TimelineView({ timeline }: TimelineViewProps) {
  if (timeline.events.length === 0 && timeline.conflicts.length === 0) {
    return <p className="empty-state">События не найдены.</p>;
  }

  return (
    <>
      <ul className="timeline-list">
        {timeline.events.map((event, index) => (
          <li key={`${event.description}-${index}`} className="timeline-item">
            <div className="timeline-meta">
              <span>{event.date ?? "дата неизвестна"}</span>
              <span className="badge">{CATEGORY_LABELS[event.category]}</span>
              <span className="badge">{event.confidence}</span>
              {event.has_date_conflict ? <span className="badge">конфликт дат</span> : null}
            </div>
            <p>{event.description}</p>
            <div className="evidence-links">
              {event.source_urls.map((url) => (
                <a key={url} href={url} target="_blank" rel="noreferrer">
                  {url}
                </a>
              ))}
            </div>
          </li>
        ))}
      </ul>
      {timeline.conflicts.length > 0 ? (
        <div className="verdict-section">
          <h3>Конфликты в данных</h3>
          <ul className="timeline-list">
            {timeline.conflicts.map((conflict, index) => (
              <li key={`${conflict.message}-${index}`} className="timeline-item conflict">
                <div className="timeline-meta">
                  <span className="badge">{CATEGORY_LABELS[conflict.category]}</span>
                  <span>{conflict.dates.join(" / ")}</span>
                </div>
                <p>{conflict.message}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
