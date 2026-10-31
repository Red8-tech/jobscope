import pandas as pd
import pytest


@pytest.fixture
def messy_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "1", "title": "Python Dev", "company": "  Acme ",
                "location": "remote", "salary": "90k-120k", "posted": "28/10/2026",
                "tags": "Python|SQL", "description": "<p>Hi</p>", "url": "u1",
                "category": "Dev",
            },
            {
                "id": "2", "title": "python dev", "company": "ACME",
                "location": "Worldwide", "salary": "", "posted": "2026-10-28",
                "tags": "", "description": "", "url": "u2", "category": "Dev",
            },
            {
                "id": "3", "title": "", "company": "Globex",
                "location": "", "salary": "", "posted": "",
                "tags": "", "description": "", "url": "u3", "category": "",
            },
        ]
    )