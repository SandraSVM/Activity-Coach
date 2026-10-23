import torch
import transformers
import pandas as pd
import transformers
import torch

prompts = pd.read_excel("src\\prompt_data.xlsx")
sys_prompts = prompts["System_prompt"]
body_prompts = prompts["Prompt_body"]

model_id = "meta-llama/Meta-Llama-3.1-8B-Instruct"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)

mssg_data = pd.DataFrame(columns=["Prompt", "Output"])


for i in range(len(prompts)):
    messages = [
    {"role": "system", "content": sys_prompts[i]},
    {"role": "user", "content": body_prompts[i]},
    ]

    outputs = pipeline(
        messages,
        max_new_tokens=256,
    )
    mssg_data.loc[len(mssg_data)] = [prompts["Full_prompt"][i], outputs[0]["generated_text"][-1]]


mssg_data.to_excel("src\\messages.xlsx")
    