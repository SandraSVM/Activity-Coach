import pandas as pd
import anthropic
import os
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))
result_data = pd.DataFrame(columns=["Prompt", "Output", "Judge"])

eval_data = pd.read_excel("src\\prompts.xlsx")

instructions = eval_data["Prompt"]
responses =   eval_data["Output"]


ABS_SYSTEM_PROMPT = "You are a fair judge assistant tasked with providing clear, objective feedback based on specific criteria, ensuring each assessment reflects the absolute standards set for performance."

ABSOLUTE_PROMPT = """###Task Description:
You will be give an instruction, a response to evaluate, and a score rubric representing an evaluation criteria.
1. Write a detailed feedback that assesses the quality of the response strictly based on the given score rubric, not evaluating in general.
2. After writing feedback, write a score that is an integer between 1 and 5. You should refer to the score rubric.
3. The output format should look as follows: "Feedback: (write a feedback for criteria) [RESULT] (an integer number between 1 and 5)"
4. Please do not generate any other opening, closing, and explanations.

###The instruction to evaluate:
{instruction}

###Response to evaluate:
{response}

###Score Rubric:
{rubric_data}
"""

rubric = """
[Criteria: Is the model proficient in following the given instructions to generate an activity recommendation message with the correct information, in the appropriate tone of voice, and exhibiting the requested type of support?]
Score 1: The model disregards the provided instructions, generating a recommendation that contains only incorrect information, an unfitting tone of voice, and does not exhibit the requested type of support.
Score 2: The model somewhat follows the provided instructions, but the message still omits most information or contains many inaccuracies. The message also does not sufficiently align with the requested tone of voice and/or type of support.
Score 3: The model mostly follows the provided instructions, and the appropriate tone of voice, as well as the requested type of support, are somewhat evident in the message. Yet, there are still notable inaccuracies, omissions, or inconsistencies that reduce the overall alignment of the message with the instructions.
Score 4: The model consistently follows the provided instructions, uses the appropriate tone of voice, and the requested type of support. Nonetheless, there may still be small oversights or deficiencies in accuracy, completeness, or alignment with the instructions.
Score 5: The model fully follows the provided instructions, and the generated message is accurate, without omissions, and fully aligned with the requested tone of voice and type of support.

Take into account that the model had to construct each message under a certain word limit. To accommodate this, some information might be left out, which is acceptable in some cases. 
The following points are small deficiencies and should be mentioned in the feedback, but should not be substantially penalized in the final score:
-	Leaving out location, or equipment
-	Leaving out bullet points
-	Not mentioning the exact weather forecast, if an indication is given of temperature (e.g., chilly or warm) and rain is mentioned when forecasted
-	Leaving out explanation for the recommendation
-	Not using the (activity) data of the user within the different support types (the model does not have access to this)

The following points count as notable inaccuracies and should have the main effect in penalizing the final score:
-	Inclusion of activities that are fully invented, missing, or adapted from the instruction 
-	Fully leaving out activity intensity/speed and/or duration
""".strip()


for i, (instruction, response) in enumerate(zip(instructions, responses)):
  user_content = ABS_SYSTEM_PROMPT + "\n\n" + ABSOLUTE_PROMPT.format(instruction=instruction,response=response, rubric_data=rubric)
  judge_response = client.messages.create(
                    model="claude-opus-5-5",
                    max_tokens=1600,
                    messages=[{"role": "user", "content": user_content}],
  )
  result_data.loc[len(result_data)] = [instruction, response, judge_response]
    

result_data.to_excel("src\\results.xlsx")