"""Normalized contribution data models — provider-agnostic."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Provider(StrEnum):
    GITHUB = "github"
    GITEA = "gitea"


class ContributionType(StrEnum):
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    REVIEW = "review"


class Contribution(BaseModel):
    """Base contribution from any provider."""

    provider: Provider
    type: ContributionType
    timestamp: datetime
    repo_name: str
    repo_url: str


class CommitContribution(Contribution):
    type: ContributionType = ContributionType.COMMIT
    sha: str
    message: str
    additions: int = 0
    deletions: int = 0


class PullRequestContribution(Contribution):
    type: ContributionType = ContributionType.PULL_REQUEST
    title: str
    number: int
    state: str  # open, closed, merged
    merged: bool = False


class IssueContribution(Contribution):
    type: ContributionType = ContributionType.ISSUE
    title: str
    number: int
    state: str  # open, closed
    labels: list[str] = Field(default_factory=list)


class ReviewContribution(Contribution):
    type: ContributionType = ContributionType.REVIEW
    pr_number: int
    pr_title: str
    state: str  # approved, changes_requested, commented


class UserProfile(BaseModel):
    """User profile from a provider."""

    provider: Provider
    username: str
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    profile_url: str
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    created_at: datetime | None = None


class RepoSummary(BaseModel):
    """Aggregated stats for a single repo."""

    name: str
    url: str
    language: str | None = None
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    reviews: int = 0
    stars: int = 0
    is_fork: bool = False


class MonthlyActivity(BaseModel):
    """Contribution count for a single month."""

    month: str  # YYYY-MM format
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    reviews: int = 0

    @property
    def total(self) -> int:
        return self.commits + self.pull_requests + self.issues + self.reviews


class CalendarDay(BaseModel):
    """A single day in the contribution calendar (from GraphQL)."""

    date: str  # YYYY-MM-DD
    count: int = 0


class ContributionSummary(BaseModel):
    """Aggregated summary of all contributions — ready for rendering."""

    profile: UserProfile
    total_commits: int = 0
    total_pull_requests: int = 0
    total_issues: int = 0
    total_reviews: int = 0
    private_contributions: int = 0
    top_repos: list[RepoSummary] = Field(default_factory=list)
    monthly_activity: list[MonthlyActivity] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)  # language -> repo count
    contribution_types: dict[str, int] = Field(default_factory=dict)  # type -> count
    calendar: list[CalendarDay] = Field(default_factory=list)  # daily activity heatmap
    narrative: str | None = None  # AI-generated narrative summary
    providers: list[str] = Field(default_factory=list)  # which providers contributed data

    @property
    def total_contributions(self) -> int:
        return self.total_commits + self.total_pull_requests + self.total_issues + self.total_reviews
