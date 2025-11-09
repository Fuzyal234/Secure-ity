import os
from functools import lru_cache
from typing import Optional

from supabase import Client, create_client


class SupabaseConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Create or return a cached Supabase client.
    Prefers SUPABASE_SERVICE_ROLE_KEY; falls back to SUPABASE_ANON_KEY.
    """
    url: Optional[str] = os.environ.get("SUPABASE_URL")
    key: Optional[str] = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise SupabaseConfigError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) must be set")

    return create_client(url, key)


