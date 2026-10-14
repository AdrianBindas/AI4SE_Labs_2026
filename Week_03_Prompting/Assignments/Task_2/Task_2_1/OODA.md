### Observe
Inspect the files in the Task_2_1 folder containing the database schema, database dump, and natural-language questions and correct answer for each question. Generate one correct SQLite query for each question that will output the correct answer. You are NOT allowed to execute SQLite engine.

### Orient
The folder Task_2_1 contains all documents relevant to the task. Identify the schema, tables, columns, relationships, available data, all questions and answers.

### Decide
Analyze each question against the schema and data. Challenge assumptions, identify ambiguities, determine the appropriate joins and operations, and establish whether the question can be answered reliably. This should be the most thorough phase.

### Act
Generate one SQLite-compatible SQL query per question, preserving the original order. Use only verified tables, columns, and relationships. Briefly document necessary assumptions.

At the very end generate a report containing:
- One SQLite query per question in a restaurants_dataset_predictions.csv
- Inference time in ms - How long did it take you to generate a solution since the moment you inspected relevant files until you generated a solution.
- Tokens and credits spent - Report this information during the same time window as inference time.