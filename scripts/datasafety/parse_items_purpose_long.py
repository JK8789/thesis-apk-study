import re
import pandas as pd

INPUT_CSV = "results/datasafety/datasafety_pairs_purpose.csv"
OUTPUT_CSV = "results/datasafety/datasafety_long.csv"

def parse_items_purpose(s):
    """
    Returns list of tuples:
      (category, item, purpose, optional)

    - Split by ';'
    - If entry has '->' or '→', parse purpose
    - If entry has no arrow, still emit row with empty purpose
    - Preserve special markers: No data collected/shared/no declared data
    """
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return []

    text = str(s).strip()
    if not text:
        return []

    text = text.replace("→", "->")

    parts = [p.strip() for p in text.split(";") if p.strip()]
    out = []

    for p in parts:
        low = p.lower().strip()

        if low in ["no data collected", "no data shared", "no declared data"]:
            out.append((p.strip(), "", "", False))
            continue

        if "->" in p:
            left, right = p.split("->", 1)
            left = left.strip()
            purpose = right.strip()
        else:
            left = p.strip()
            purpose = ""

        if ":" in left:
            cat, item = left.split(":", 1)
            cat = cat.strip()
            item = item.strip()
        else:
            cat = ""
            item = left.strip()

        optional = False
        if re.search(r"(·|•)\s*Optional\b", item):
            item = re.sub(r"(·|•)\s*Optional\b", "", item).strip()
            optional = True
        elif item.rstrip().endswith("Optional"):
            item = re.sub(r"\bOptional\b", "", item).strip(" ·•")
            optional = True

        out.append((cat, item, purpose, optional))

    return out

def infer_store(link: str) -> str:
    if not isinstance(link, str):
        return ""
    if "play.google.com" in link:
        return "googleplay"
    if "apps.apple.com" in link:
        return "appstore"
    if "rustore.ru" in link:
        return "rustore"
    return ""

def main():
    df = pd.read_csv(INPUT_CSV)

    rows = []
    for _, r in df.iterrows():
        package = r.get("package", "")
        app = r.get("app_name", r.get("app", ""))  # supports either column name
        link = r.get("link", "")
        store = infer_store(link)

        # these are the columns created earlier in your file
        collected_str = r.get("collected_items:data->purpose", "")
        shared_str = r.get("shared_items:data->purpose", "")

        for cat, item, purpose, optional in parse_items_purpose(collected_str):
            rows.append({
                "package": package,
                "app": app,
                "link": link,
                "store": store,
                "direction": "collected",
                "category": cat,
                "item": item,
                "purpose": purpose,
                "optional": optional
            })

        for cat, item, purpose, optional in parse_items_purpose(shared_str):
            rows.append({
                "package": package,
                "app": app,
                "link": link,
                "store": store,
                "direction": "shared",
                "category": cat,
                "item": item,
                "purpose": purpose,
                "optional": optional
            })

    out_df = pd.DataFrame(rows, columns=[
        "package","app","link","store","direction","category","item","purpose","optional"
    ])
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved: {OUTPUT_CSV} ({len(out_df)} rows)")

if __name__ == "__main__":
    main()

