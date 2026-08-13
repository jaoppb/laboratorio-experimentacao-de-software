import os
import csv
import requests
from datetime import datetime


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

PROJECT_OWNER = "jaoppb"
PROJECT_NUMBER = 3

QUERY = """
query($login: String!, $number: Int!, $after: String) {
  user(login: $login) {
    projectV2(number: $number) {
      items(first: 50, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          content {
            ... on Issue {
              number
              title
            }
          }
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldTextValue {
                text
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldUserValue {
                users(first: 5) {
                  nodes {
                    login
                  }
                }
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def run_query(after=None):
    variables = {"login": PROJECT_OWNER, "number": PROJECT_NUMBER, "after": after}
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


def extract_snapshot():
    rows = []
    after = None
    while True:
        data = run_query(after)
        project = data["data"]["user"]["projectV2"]
        for item in project["items"]["nodes"]:
            content = item.get("content") or {}
            row = {
                "issue_number": content.get("number", ""),
                "title": content.get("title", ""),
                "status": "",
                "assignee": "",
                "lab": "",
                "sprint": "",
                "rq": "",
            }
            for fv in item["fieldValues"]["nodes"]:
                field_name = fv.get("field", {}).get("name", "")
                if field_name == "Status":
                    row["status"] = fv.get("name", "")
                elif field_name == "Lab":
                    row["lab"] = fv.get("name", "")
                elif field_name == "Sprint":
                    row["sprint"] = fv.get("name", "")
                elif field_name == "RQ":
                    row["rq"] = fv.get("text", "")
                elif field_name == "Assignees":
                    users = fv.get("users", {}).get("nodes", [])
                    row["assignee"] = ", ".join(u["login"] for u in users)
            rows.append(row)

        page_info = project["items"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]

    return rows


def save_csv(rows, filename=None):
    if filename is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = os.path.join(script_dir, "..", "dados", f"snapshot_{date_str}.csv")

    filename = os.path.abspath(filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Snapshot salvo em {filename}")


if __name__ == "__main__":
    rows = extract_snapshot()
    for row in rows:
        print(row)
    save_csv(rows)