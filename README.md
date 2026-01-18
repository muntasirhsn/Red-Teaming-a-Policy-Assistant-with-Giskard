# Red-Teaming-a-Policy-Assistant-with-Giskard
This project demonstrates iterative red-teaming of a policy assistant designed to answer questions about a government-style digital services policy, while strictly avoiding legal advice, speculation, or guidance on bypassing safeguards. The focus is on safety evaluation, failure analysis, and mitigation, rather than model fine-tuning.


### Model Separation Strategy
The system intentionally uses **different models for generation and evaluation**:
* Query responses are generated using **gpt-4o-mini**
* Safety evaluation is performed using **gpt-4o** via Giskard detectors
This reflects common red-teaming practice: lighter models are sufficient for generation, while **stronger models provide more reliable safety judgments**. Separating generation and evaluation also avoids self-evaluation effects and keeps evaluation costs controlled.

### Initial Evaluation
The assistant was evaluated using **Giskard** across prompt-injection, misuse, and bias detectors. The scan identified multiple failures where the agent did not attempt to answer questions based on the provided policy document. These were not hallucinations or unsafe outputs, but overly conservative refusals.

<img src="images/giskard1.png?raw=true"/> Figure 1: Initial scan results from Giskard.

### Analysis
The root cause was **over-refusal**.
The safety layer correctly blocked requests involving legal advice, speculation, or bypassing safeguards, but also refused some benign questions that could have been partially answered using neutral policy language. This reduced policy grounding and triggered Giskard failures.

### Mitigation
The refusal strategy was refined to better distinguish between:
* questions requiring refusal, and
* questions that can be answered safely using policy text alone.
Refusals were standardized using fixed, auditable messages, while benign queries now trigger policy-based responses where possible. Safety guarantees were preserved.

### Outcome
A follow-up Giskard scan showed improved behavior:
* fewer false positives for “did not attempt to answer”
* stronger grounding in policy text
* no regression in prompt-injection or misuse resistance

<img src="images/giskard2.png?raw=true"/> Figure 2: Post mitigation scan results from Giskard.

This project demonstrates a complete red-teaming loop — evaluation, failure analysis, mitigation, and re-evaluation — and shows how safety behavior can be systematically improved without increasing risk or cost.
