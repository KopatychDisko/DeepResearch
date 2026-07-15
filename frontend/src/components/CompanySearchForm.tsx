import { useLanguage } from "../lib/i18n";

interface CompanySearchFormProps {
  companyName: string;
  companyUrl: string;
  companyDescription: string;
  isLoading: boolean;
  onCompanyNameChange: (value: string) => void;
  onCompanyUrlChange: (value: string) => void;
  onCompanyDescriptionChange: (value: string) => void;
  onSubmit: () => void;
}

export function CompanySearchForm({
  companyName,
  companyUrl,
  companyDescription,
  isLoading,
  onCompanyNameChange,
  onCompanyUrlChange,
  onCompanyDescriptionChange,
  onSubmit,
}: CompanySearchFormProps) {
  const { t } = useLanguage();

  return (
    <form
      className="search-form-stack"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="search-form">
        <input
          type="text"
          value={companyName}
          placeholder={t.companyNamePlaceholder}
          onChange={(event) => onCompanyNameChange(event.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || companyName.trim().length < 2}>
          {isLoading ? t.submitting : t.submit}
        </button>
      </div>
      <input
        className="search-url-input"
        type="url"
        value={companyUrl}
        placeholder={t.companyUrlPlaceholder}
        onChange={(event) => onCompanyUrlChange(event.target.value)}
        disabled={isLoading}
      />
      <textarea
        className="search-description-input"
        value={companyDescription}
        placeholder={t.companyDescriptionPlaceholder}
        rows={3}
        maxLength={500}
        onChange={(event) => onCompanyDescriptionChange(event.target.value)}
        disabled={isLoading}
      />
    </form>
  );
}
