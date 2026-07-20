import { useLanguage, type Locale } from "../lib/i18n";

interface LanguageToggleProps {
  disabled?: boolean;
  lockedHint?: string;
}

export function LanguageToggle({ disabled = false, lockedHint }: LanguageToggleProps) {
  const { locale, setLocale } = useLanguage();

  function selectLanguage(nextLocale: Locale): void {
    if (disabled) {
      return;
    }
    setLocale(nextLocale);
  }

  return (
    <div className="language-toggle-wrap">
      <div className="language-toggle" role="group" aria-label="Language">
        <button
          type="button"
          className={locale === "ru" ? "lang-btn active" : "lang-btn"}
          disabled={disabled}
          aria-disabled={disabled}
          onClick={() => selectLanguage("ru")}
        >
          RU
        </button>
        <button
          type="button"
          className={locale === "en" ? "lang-btn active" : "lang-btn"}
          disabled={disabled}
          aria-disabled={disabled}
          onClick={() => selectLanguage("en")}
        >
          EN
        </button>
      </div>
      {disabled && lockedHint !== undefined ? (
        <span className="language-locked-hint">{lockedHint}</span>
      ) : null}
    </div>
  );
}
