"""hh.ru vacancy analysis domain models."""

from __future__ import annotations

from typing import Self

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from agents.models.enums import HhVacancyStatus


class HhSalaryRange(BaseModel):
    """Salary range parsed from hh.ru vacancy list or detail payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    from_amount: int | None
    to_amount: int | None
    currency: str | None
    gross: bool | None


def format_hh_salary_text(salary: HhSalaryRange | None) -> str | None:
    """Format hh.ru salary range for API and frontend display."""
    if salary is None:
        return None
    currency_suffix: str = f" {salary.currency}" if salary.currency else ""
    gross_suffix: str = " gross" if salary.gross is True else ""
    if salary.from_amount is not None and salary.to_amount is not None:
        return f"{salary.from_amount:,} – {salary.to_amount:,}{currency_suffix}{gross_suffix}".replace(",", " ")
    if salary.from_amount is not None:
        return f"from {salary.from_amount:,}{currency_suffix}{gross_suffix}".replace(",", " ")
    if salary.to_amount is not None:
        return f"up to {salary.to_amount:,}{currency_suffix}{gross_suffix}".replace(",", " ")
    return None


class HhVacancyItem(BaseModel):
    """Single active vacancy row sourced from api.hh.ru."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    vacancy_id: str
    title: str
    url: AnyHttpUrl
    area_name: str | None
    salary: HhSalaryRange | None
    employment_type: str | None
    schedule: str | None
    experience: str | None
    working_conditions: list[str]
    published_at: str | None
    archived: bool | None = None
    key_skills: list[str] = Field(default_factory=list)
    description_plain: str | None = None
    employer_trusted: bool | None = None
    salary_text: str | None = None
    location_text: str | None = None
    schedule_text: str | None = None

    @model_validator(mode="after")
    def populate_display_fields(self) -> Self:
        """Derive salary_text, location_text, and schedule_text from raw vacancy fields."""
        updates: dict[str, str | None] = {}
        if self.salary_text is None:
            updates["salary_text"] = format_hh_salary_text(self.salary)
        if self.location_text is None:
            updates["location_text"] = self.area_name
        if self.schedule_text is None:
            schedule_parts: list[str] = [
                part
                for part in (self.schedule, self.employment_type)
                if part is not None and part.strip() != ""
            ]
            updates["schedule_text"] = ", ".join(schedule_parts) if schedule_parts else None
        if not updates:
            return self
        return self.model_copy(update=updates)


class HhEmployerRating(BaseModel):
    """Employer rating and trust signals when present in hh.ru profile data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    average_score: float | None
    reviews_count: int | None
    recommendation_percent: float | None
    trusted: bool | None
    accredited_it_employer: bool | None
    source_url: AnyHttpUrl | None


class HhVacancySummary(BaseModel):
    """Employer profile summary attached to vacancy analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    employer_id: str
    name: str
    profile_url: AnyHttpUrl
    site_url: AnyHttpUrl | None
    open_vacancies_count: int | None
    rating: HhEmployerRating


class StructuredHhVacancyAssessment(BaseModel):
    """Structured LLM output for hh.ru vacancy salary and conditions summaries."""

    model_config = ConfigDict(extra="forbid")

    salary_summary: str = Field(min_length=1)
    conditions_summary: str = Field(min_length=1)
    employer_rating_text: str = Field(min_length=1)


class StructuredHhEmployerSearchReformulation(BaseModel):
    """Structured LLM output with alternate hh.ru employer search strings."""

    model_config = ConfigDict(extra="forbid")

    search_queries: list[str] = Field(min_length=1, max_length=5)


class HhVacancyAnalysis(BaseModel):
    """Structured hh.ru vacancy assessment block stored separately from timeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HhVacancyStatus
    message: str
    search_query: str
    employer: HhVacancySummary | None
    vacancies: list[HhVacancyItem]
    salary_summary: str
    conditions_summary: str
    fetched_at: str
    search_queries_tried: list[str] = Field(default_factory=list)
    matched_search_query: str | None = None
    employer_name: str | None = None
    employer_profile_url: str | None = None
    employer_rating: float | None = None
    employer_rating_count: int | None = None

    @model_validator(mode="after")
    def populate_api_fields(self) -> Self:
        """Flatten employer profile fields for frontend API contract."""
        updates: dict[str, object] = {}
        if self.employer is not None:
            if self.employer_name is None:
                updates["employer_name"] = self.employer.name
            if self.employer_profile_url is None:
                updates["employer_profile_url"] = str(self.employer.profile_url)
            rating = self.employer.rating
            if self.employer_rating is None and rating.available:
                updates["employer_rating"] = rating.average_score
            if self.employer_rating_count is None and rating.available:
                updates["employer_rating_count"] = rating.reviews_count
        if not updates:
            return self
        return self.model_copy(update=updates)
