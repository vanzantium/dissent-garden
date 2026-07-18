# Comparative Evaluation Plan

Dissent Garden should be judged against the thing it replaces: one polished
model answer to the same evidence-bound decision. This plan deliberately records
no results until the live GPT-5.6 runs and blind review have happened.

## Comparison

For every scenario in `evals/scenarios.json`, generate:

1. a baseline answer from one GPT-5.6 call using the question, context,
   constraints, and evidence;
2. a Dissent Garden result using the same inputs and normal four-pass pipeline.

Remove product labels, randomize A/B order, and have at least three reviewers
score each pair independently. Reviewers should not know which answer came from
which system.

## Rubric

Score each output from 1 (poor) to 5 (excellent):

| Dimension | What the reviewer checks |
| --- | --- |
| Decision usefulness | Is there a clear, bounded course of action? |
| Evidence discipline | Are facts distinguished from inference and tied to supplied evidence? |
| Consequential risk | Does the answer surface the failure mode most likely to change the decision? |
| Preserved uncertainty | Does it retain an unresolved tension instead of smoothing it away? |
| Reversibility | Is the next test cheap, measurable, and capable of changing the decision? |

Also count objective defects:

- unsupported factual claims;
- supplied evidence items materially misrepresented;
- recommendations that violate an explicit constraint;
- repeated dissent that adds no new risk, evidence conflict, or test.

## Token and memory checks

- Record actual Responses API input/output usage for both systems.
- Repeat an unchanged Dissent Garden request and verify zero new model calls plus
  avoided tokens equal to the original receipt's recorded usage.
- Add a correction, repeat again, and verify the stale receipt is not reused.
- Run a related decision and verify the memory brief remains at or below 1,800
  characters and labels old conclusions as context rather than evidence.

## Reporting

Publish the scenario-level scores, reviewer count, model snapshot/date, prompts,
actual token usage, and disagreements between reviewers. Report medians and raw
counts; do not convert the claim-survival rate into a confidence or truth score.

