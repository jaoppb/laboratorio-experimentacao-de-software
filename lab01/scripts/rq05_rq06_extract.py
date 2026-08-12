import os
import csv
import requests
def load_env(filepath=None):
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(filepath, "r") as f:
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
        primaryLanguage {
          name
        }
        closedIssues: issues(states: CLOSED) {
          totalCount
        }
        openIssues: issues(states: OPEN) {
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
        primary_language = repo["primaryLanguage"]["name"] if repo["primaryLanguage"] else None
        closed_issues = repo["closedIssues"]["totalCount"]
        open_issues = repo["openIssues"]["totalCount"]
        total_issues = closed_issues + open_issues
        closed_ratio = (closed_issues / total_issues) if total_issues > 0 else None
        results.append(
            {
                "repo": repo["nameWithOwner"],
                "primary_language": primary_language,
                "closed_issues": closed_issues,
                "open_issues": open_issues,
                "total_issues": total_issues,
                "closed_issues_ratio": closed_ratio,
            }
        )
    return results
def save_csv(rows, filename=None):
    if filename is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(script_dir, "..", "dados", "rq05_rq06_sample.csv")
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