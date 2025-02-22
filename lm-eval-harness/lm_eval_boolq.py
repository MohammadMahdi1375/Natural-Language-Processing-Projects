""""
In orderr to process the 'Hellaswag' data for passing to the model, add the following code to this address:
./lm-evaluation-harness/lm_eval/evaluator.py ----> <<evaluate>> function ----> before 
                                                   resps = getattr(lm, reqtype)(cloned_reqs)

    1) Query: Main Context
    2) choices: options
    3) label: true answer
    4) tokenizer(Query) + tokenizer(choice)[:-2]: The input of the model
    5) Sum up the the likelihoods frm last 
columns = ['ind', 'Query', 'Choices', 'label']
ds = []
query = ""
ind = 0
choices = []
data_list = []
for idx, data in enumerate(requests['loglikelihood']):
    if (data.args[0] != query):
        if (idx != 0):
            data_list.append(ind)
            data_list.append(query)
            data_list.append(choices)
            data_list.append(label)
            ds.append(data_list)

            choices = []
            data_list = []
            ind += 1

        query = data.args[0]
        choices.append(data.args[1])
        label = data.doc['label']
    else:
        choices.append(data.args[1])

df = pd.DataFrame(ds, columns=columns)
df.to_json('/home/mohammad-m/TTT/RL/lm_eval_data/boolq_validation.json', orient="records", lines=True)
"""


import re
import csv
import torch
import string
import numpy as np
import pandas as pd
from collections import Counter
import torch.nn.functional as F
from datasets import load_dataset
from tqdm import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoModelForCausalLM, pipeline


dataset = pd.read_json("./lm_eval_data/boolq_validation.json", orient='records', lines=True)

model_name = "meta-llama/Llama-3.2-1B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")

model_results = []
for idx in tqdm(range(len(dataset)), desc="Processing"):
    loglokelihoods = []
    choice_lens = []
    true_output = dataset['label'][idx]
    if True:
        for choice in dataset['Choices'][idx]:
            prompt = dataset['Query'][idx] + choice
            tokenizer_choice = tokenizer(choice, return_tensors='pt', add_special_tokens=False)
            tokenized = tokenizer(prompt, return_tensors='pt', add_special_tokens=False)
            
            context_length = tokenized['input_ids'].shape[1] - 1
            choice_length = tokenizer_choice['input_ids'].shape[1]

            output = model(tokenized['input_ids']).logits
            multi_logits = F.log_softmax(output, dim=-1)

            logits = multi_logits[:, context_length - choice_length: context_length, :]
            logits = torch.gather(logits, 2, tokenizer_choice['input_ids'].unsqueeze(-1)).squeeze(-1)  # [1, seq]

            loglokelihoods.append(float(logits.sum()))
        
        pred_output_choice = np.argmax(loglokelihoods)

        if pred_output_choice == true_output: model_results.append(1.0)
        else: model_results.append(0.0)


    
print("=========================================================================")
print(f"Accuracy = {np.sum(model_results) / len(model_results)}")        
print("=========================================================================")
