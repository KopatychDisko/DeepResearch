import { useLanguage, type Locale } from "../lib/i18n";

export function LanguageToggle() {
  const { locale, setLocale } = useLanguage();

  function selectLanguage(nextLocale: Locale): void {
    setLocale(nextLocale);
  }

  return (
    <div className="language-toggle" role="group" aria-label="Language">
      <button
        type="button"
        className={locale === "ru" ? "lang-btn active" : "lang-btn"}
        onClick={() => selectLanguage("ru")}
      >
        RU
      </button>
      <button
        type="button"
        className={locale === "en" ? "lang-btn active" : "lang-btn"}
        onClick={() => selectLanguage("en")}
      >
        EN
      </button>
    </div>
  );
}
