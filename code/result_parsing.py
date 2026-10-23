import re, ast
import pandas as pd

def extract_text(s):
    # Find all TextBlock(... text='...' ...) contents
    matches = re.findall(r"TextBlock\(.*?text=('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")", s, flags=re.S)
    return "\n".join(ast.literal_eval(m) for m in matches)

df = pd.read_excel("src\\result_data_0_extra_criteria.xlsx")
df["clean"] = df["Judge"].astype(str).apply(extract_text)
df["score"] = df["clean"].str.extract(r"\[RESULT\]\s*(\d+)").astype(float)

df.to_excel("src\\results_0_extra_criteria_cleaned.xlsx")