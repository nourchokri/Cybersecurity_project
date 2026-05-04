from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _load_env_file(path: Path) -> None:
  """Load KEY=VALUE pairs from a .env file without overriding existing env vars."""

  if not path.exists() or not path.is_file():
    return

  for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
      continue
    if "=" not in line:
      continue
    k, v = line.split("=", 1)
    k = k.strip()
    v = v.strip().strip('"').strip("'")
    if not k:
      continue
    if k not in os.environ:
      os.environ[k] = v


@dataclass(frozen=True)
class CertDbConfig:
  """DB-only configuration for CERT + LDAP tools.

  These tools query Supabase Postgres tables directly (no CSV reads).
  Provide a Postgres DSN via environment variables.
  """

  dsn: str

  # Table names (override if you used different names/schema)
  ldap_table: str = "ldap_users"
  psych_table: str = "cert_psychometrics"
  email_table: str = "cert_email"
  file_table: str = "cert_file"

  # Optional: reuse existing mock JSON policy/rules until you migrate those too.
  policy_json: Optional[Path] = None
  rule_library_json: Optional[Path] = None

  @staticmethod
  def from_env() -> "CertDbConfig":
    # Convenience: if user put DSN into project-root .env, load it.
    # This keeps setup simple on Windows where env vars are often session-scoped.
    try:
      _load_env_file(Path(".env"))
    except Exception:
      pass

    dsn = (
      os.getenv("SUPABASE_DB_URL")
      or os.getenv("DATABASE_URL")
      or os.getenv("POSTGRES_DSN")
      or ""
    ).strip()
    if not dsn:
      raise ValueError(
        "Missing database DSN. Set SUPABASE_DB_URL (recommended) or DATABASE_URL / POSTGRES_DSN."
      )
    return CertDbConfig(dsn=dsn)

  def resolve(self) -> "CertDbConfig":
    """Normalize optional JSON file paths (kept for policy/rule_library tools)."""

    def p(x: Optional[Path]) -> Optional[Path]:
      return Path(x).expanduser().resolve() if x is not None else None

    return CertDbConfig(
      dsn=self.dsn,
      ldap_table=self.ldap_table,
      psych_table=self.psych_table,
      email_table=self.email_table,
      file_table=self.file_table,
      policy_json=p(self.policy_json),
      rule_library_json=p(self.rule_library_json),
    )
