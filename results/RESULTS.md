# Results

All numbers below were produced by `make report` from the raw episode logs in `results/raw/`.
Models run locally with llama.cpp (Q4_K_M GGUF, temperature 0). 95% Wilson intervals in brackets.

![tradeoff](tradeoff.png)

## llama3.2-3B-Q4_K_M

16 benign tasks, 192 attacked episodes per defense.

| Defense | Benign utility | Attack success (all) | ASR: tool actions | ASR: phishing reply | Utility under attack | LLM calls / episode |
|---|---|---|---|---|---|---|
| No defense | 43.8% [23-67] | **60.9% [54-68]** | 73.6% [66-80] | 22.9% [13-37] | 14.6% [10-20] | 5.59 |
| Sandwich reminder | 43.8% [23-67] | **28.1% [22-35]** | 34.7% [27-43] | 8.3% [3-20] | 32.3% [26-39] | 5.47 |
| Tool-call policy guard | 43.8% [23-67] | **5.7% [3-10]** | 0.0% [0-3] | 22.9% [13-37] | 9.4% [6-14] | 5.62 |
| Layered: classifier + sandwich + guard | 37.5% [18-61] | **0.0% [0-2]** | 0.0% [0-3] | 0.0% [0-7] | 33.9% [28-41] | 5.46 |

Attack success by family (rows) and defense (columns):

| Family | none | sandwich | tool_guard | layered |
|---|---|---|---|---|
| naive | 81.2% | 50.0% | 12.5% | 0.0% |
| ignore_previous | 100.0% | 75.0% | 25.0% | 0.0% |
| important_instructions | 50.0% | 37.5% | 0.0% | 0.0% |
| fake_system | 75.0% | 12.5% | 6.2% | 0.0% |
| fake_completion | 75.0% | 62.5% | 0.0% | 0.0% |
| combined | 87.5% | 50.0% | 18.8% | 0.0% |
| authority | 68.8% | 6.2% | 0.0% | 0.0% |
| urgency | 37.5% | 6.2% | 0.0% | 0.0% |
| tool_spoof | 25.0% | 12.5% | 0.0% | 0.0% |
| hidden_html | 68.8% | 6.2% | 0.0% | 0.0% |
| base64 | 0.0% | 0.0% | 0.0% | 0.0% |
| multilingual | 62.5% | 18.8% | 6.2% | 0.0% |

Attack success by attacker goal:

| Goal | none | sandwich | tool_guard | layered |
|---|---|---|---|---|
| exfiltrate (data stealing) | 64.6% | 43.8% | 0.0% | 0.0% |
| payment (direct harm) | 72.9% | 18.8% | 0.0% | 0.0% |
| delete (direct harm) | 83.3% | 41.7% | 0.0% | 0.0% |
| phishing (output manipulation) | 22.9% | 8.3% | 22.9% | 0.0% |

## qwen2.5-3B-Q4_K_M

16 benign tasks, 192 attacked episodes per defense.

| Defense | Benign utility | Attack success (all) | ASR: tool actions | ASR: phishing reply | Utility under attack | LLM calls / episode |
|---|---|---|---|---|---|---|
| No defense | 87.5% [64-97] | **38.5% [32-46]** | 37.5% [30-46] | 41.7% [29-56] | 62.0% [55-69] | 2.99 |
| Spotlighting: delimiters | 87.5% [64-97] | **31.2% [25-38]** | 31.9% [25-40] | 29.2% [18-43] | 63.0% [56-70] | 2.86 |
| Spotlighting: datamarking | 81.2% [57-93] | **28.1% [22-35]** | 27.8% [21-36] | 29.2% [18-43] | 65.6% [59-72] | 2.52 |
| Sandwich reminder | 93.8% [72-99] | **16.1% [12-22]** | 19.4% [14-27] | 6.2% [2-17] | 90.6% [86-94] | 2.81 |
| Injection classifier (filter) | 87.5% [64-97] | **13.5% [9-19]** | 13.2% [9-20] | 14.6% [7-27] | 83.9% [78-88] | 2.77 |
| LLM self-check (filter) | 75.0% [51-90] | **25.0% [19-32]** | 20.8% [15-28] | 37.5% [25-52] | 22.4% [17-29] | 5.31 |
| Tool-call policy guard | 87.5% [64-97] | **10.4% [7-16]** | 0.0% [0-3] | 41.7% [29-56] | 53.1% [46-60] | 3.11 |
| Layered: classifier + sandwich + guard | 93.8% [72-99] | **0.0% [0-2]** | 0.0% [0-3] | 0.0% [0-7] | 97.9% [95-99] | 2.65 |

Attack success by family (rows) and defense (columns):

| Family | none | delimit | datamark | sandwich | classifier | self_check | tool_guard | layered |
|---|---|---|---|---|---|---|---|---|
| naive | 50.0% | 25.0% | 31.2% | 6.2% | 43.8% | 43.8% | 12.5% | 0.0% |
| ignore_previous | 81.2% | 56.2% | 50.0% | 62.5% | 0.0% | 43.8% | 18.8% | 0.0% |
| important_instructions | 37.5% | 25.0% | 43.8% | 12.5% | 0.0% | 0.0% | 6.2% | 0.0% |
| fake_system | 18.8% | 25.0% | 6.2% | 0.0% | 0.0% | 12.5% | 6.2% | 0.0% |
| fake_completion | 81.2% | 75.0% | 75.0% | 43.8% | 68.8% | 56.2% | 25.0% | 0.0% |
| combined | 68.8% | 50.0% | 50.0% | 43.8% | 0.0% | 75.0% | 12.5% | 0.0% |
| authority | 25.0% | 6.2% | 6.2% | 0.0% | 0.0% | 0.0% | 6.2% | 0.0% |
| urgency | 12.5% | 18.8% | 18.8% | 12.5% | 12.5% | 6.2% | 6.2% | 0.0% |
| tool_spoof | 37.5% | 37.5% | 18.8% | 6.2% | 0.0% | 43.8% | 18.8% | 0.0% |
| hidden_html | 12.5% | 6.2% | 6.2% | 6.2% | 0.0% | 6.2% | 0.0% | 0.0% |
| base64 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| multilingual | 37.5% | 50.0% | 31.2% | 0.0% | 37.5% | 12.5% | 12.5% | 0.0% |

Attack success by attacker goal:

| Goal | none | delimit | datamark | sandwich | classifier | self_check | tool_guard | layered |
|---|---|---|---|---|---|---|---|---|
| exfiltrate (data stealing) | 37.5% | 31.2% | 29.2% | 20.8% | 16.7% | 25.0% | 0.0% | 0.0% |
| payment (direct harm) | 29.2% | 20.8% | 18.8% | 14.6% | 8.3% | 12.5% | 0.0% | 0.0% |
| delete (direct harm) | 45.8% | 43.8% | 35.4% | 22.9% | 14.6% | 25.0% | 0.0% | 0.0% |
| phishing (output manipulation) | 41.7% | 29.2% | 29.2% | 6.2% | 14.6% | 37.5% | 41.7% | 0.0% |

## qwen2.5-7B-Q4_K_M

16 benign tasks, 192 attacked episodes per defense.

| Defense | Benign utility | Attack success (all) | ASR: tool actions | ASR: phishing reply | Utility under attack | LLM calls / episode |
|---|---|---|---|---|---|---|
| No defense | 93.8% [72-99] | **48.4% [41-55]** | 49.3% [41-57] | 45.8% [33-60] | 64.1% [57-71] | 2.47 |
| Layered: classifier + sandwich + guard | 93.8% [72-99] | **0.5% [0-3]** | 0.0% [0-3] | 2.1% [0-11] | 92.7% [88-96] | 2.58 |

Attack success by family (rows) and defense (columns):

| Family | none | layered |
|---|---|---|
| naive | 56.2% | 6.2% |
| ignore_previous | 93.8% | 0.0% |
| important_instructions | 68.8% | 0.0% |
| fake_system | 56.2% | 0.0% |
| fake_completion | 87.5% | 0.0% |
| combined | 87.5% | 0.0% |
| authority | 0.0% | 0.0% |
| urgency | 18.8% | 0.0% |
| tool_spoof | 0.0% | 0.0% |
| hidden_html | 18.8% | 0.0% |
| base64 | 0.0% | 0.0% |
| multilingual | 93.8% | 0.0% |

Attack success by attacker goal:

| Goal | none | layered |
|---|---|---|
| exfiltrate (data stealing) | 47.9% | 0.0% |
| payment (direct harm) | 52.1% | 0.0% |
| delete (direct harm) | 47.9% | 0.0% |
| phishing (output manipulation) | 45.8% | 2.1% |

![asr by family](asr_by_family.png)

## Detector evaluation

Classifier trained on 845 public attack strings and 6328 benign texts; threshold set for 1% FPR on held-out benign text (validation TPR 90.3%, FPR 1.0%).
Below: detection rate on this repo's attack families (4 goals each, never seen in training) and false-positive rate on 26 benign workspace segments.

| Family | Classifier | LLM self-check |
|---|---|---|
| naive | 0% | 100% |
| ignore_previous | 100% | 100% |
| important_instructions | 100% | 100% |
| fake_system | 100% | 100% |
| fake_completion | 100% | 75% |
| combined | 100% | 100% |
| authority | 100% | 100% |
| urgency | 0% | 100% |
| tool_spoof | 100% | 100% |
| hidden_html | 100% | 100% |
| base64 | 100% | 75% |
| multilingual | 0% | 100% |
| **false positives (benign)** | 3.8% | 15.4% |

## Adaptive attacker (ASR@k)

Round 1 is the static `important_instructions` injection; later rounds are rewritten by the attacker LLM after seeing what the agent did.

| Target | Attacker | Defense | pairs | ASR@1 | ASR@3 | ASR@5 |
|---|---|---|---|---|---|---|
| qwen2.5-3B-Q4_K_M | qwen2.5-3B-Q4_K_M | sandwich | 16 | 0.0% [0-19] | 18.8% [7-43] | 25.0% [10-49] |
| qwen2.5-3B-Q4_K_M | qwen2.5-3B-Q4_K_M | classifier | 16 | 0.0% [0-19] | 25.0% [10-49] | 25.0% [10-49] |
