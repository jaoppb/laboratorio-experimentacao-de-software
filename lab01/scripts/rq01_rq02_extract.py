import os
import csv
import requests
from datetime import datetime, timezone


def load_env(filepath=None):
    if filepath is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_paths = [
            os.path.join(script_dir, ".env"),
            os.path.join(script_dir, "..", ".env"),
            os.path.join(os.getcwd(), ".env"),
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                filepath = path
                break

    if filepath is None:
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("'\"")
    except FileNotFoundError:
        pass


load_env()
TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    raise ValueError("GITHUB_TOKEN não foi encontrado. Verifique se ele está definido no arquivo .env ou no ambiente.")

GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
SAMPLE_SIZE = 10

QUERY = """
query($searchQuery: String!, $first: Int!) {
  search(query: $searchQuery, type: REPOSITORY, first: $first) {
    nodes {
      ... on Repository {
        nameWithOwner
        createdAt
        mergedPRs: pullRequests(states: MERGED) {
          totalCount
        }
      }
    }
  }
}
"""


def run_query(search_query, first):
    variables = {"searchQuery": search_query, "first": first}
    response = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": variables},
        headers=HEADERS,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload


def extract_sample(sample_size):
    data = run_query("stars:>1 sort:stars-desc", sample_size)
    results = []
    for repo in data["data"]["search"]["nodes"]:
        created_at = datetime.fromisoformat(repo["createdAt"].replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created_at).days
        results.append(
            {
                "repo": repo["nameWithOwner"],
                "created_at": repo["createdAt"],
                "age_days": age_days,
                "merged_pull_requests": repo["mergedPRs"]["totalCount"],
            }
        )
    return results


def save_csv(rows, filename=None):
    if filename is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(script_dir, "..", "dados", "rq01_rq02_sample.csv")

    filename = os.path.abspath(filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    rows = extract_sample(SAMPLE_SIZE)
    for row in rows:
        print(row)
    save_csv(rows)