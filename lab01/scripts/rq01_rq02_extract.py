import os
import csv
import requests
from datetime import datetime, timezone
 
TOKEN = os.environ.get("GITHUB_TOKEN", "COLE_SEU_TOKEN_AQUI")
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
 
 
def save_csv(rows, filename="rq01_rq02_sample.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
 
 
if __name__ == "__main__":
    rows = extract_sample(SAMPLE_SIZE)
    for row in rows:
        print(row)
    save_csv(rows)