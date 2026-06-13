# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

     My domain is courses that a Georgia Tech OMSCS student interested in Artificial Intelligence might consider. This project ingests public OMSCentral review pages for Georgia Tech OMSCS courses that are relevant to or commonly considered by students pursuing the Artificial Intelligence specialization. Each course review page is treated as one source document. The guide summarizes student-reported patterns about workload, difficulty, course organization, teaching support, assignments, and perceived usefulness. This project is unofficial and should not be treated as an official Georgia Tech evaluation system. 

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | OMSCentral – Artificial Intelligence Reviews | Public student reviews for Georgia Tech OMSCS Artificial Intelligence, including workload, difficulty, assignments, course structure, and student experience. | https://www.omscentral.com/courses/artificial-intelligence/reviews |
| 2 | OMSCentral – Knowledge-Based AI Reviews | Public student reviews for Knowledge-Based AI, including feedback on course organization, assignments, workload, and usefulness for AI-focused students. | https://www.omscentral.com/courses/knowledge-based-ai/reviews |
| 3 | OMSCentral – Machine Learning Reviews | Public student reviews for Machine Learning, including comments on difficulty, workload, projects, exams, and course expectations. | https://www.omscentral.com/courses/machine-learning/reviews |
| 4 | OMSCentral – Introduction to Graduate Algorithms Reviews | Public student reviews for CS 6515 Introduction to Graduate Algorithms, an algorithms/design core option relevant to OMSCS students pursuing the AI specialization. | https://www.omscentral.com/courses/introduction-to-graduate-algorithms/reviews |
| 5 | OMSCentral – AI, Ethics, and Society Reviews | Public student reviews for AI, Ethics, and Society, including feedback on readings, assignments, workload, and ethical/social dimensions of AI. | https://www.omscentral.com/courses/ai-ethics-and-society/reviews |
| 6 | OMSCentral – Human-Computer Interaction Reviews | Public student reviews for Human-Computer Interaction, including feedback on course structure, assignments, project work, workload, and student experience. | https://www.omscentral.com/courses/human-computer-interaction/reviews |
| 7 | OMSCentral – Introduction to Computer Vision Reviews | Public student reviews for Introduction to Computer Vision, including comments on programming assignments, math difficulty, workload, and course usefulness. | https://www.omscentral.com/courses/introduction-to-computer-vision/reviews |
| 8 | OMSCentral – Game Artificial Intelligence Reviews | Public student reviews for Game AI, including feedback on applied AI concepts, assignments, projects, workload, and course enjoyment. | https://www.omscentral.com/courses/game-artificial-intelligence/reviews |
| 9 | OMSCentral – Deep Learning Reviews | Public student reviews for Deep Learning, including comments on projects, mathematical depth, programming workload, and usefulness for AI/ML students. | https://www.omscentral.com/courses/deep-learning/reviews |
| 10 | OMSCentral – Natural Language Processing Reviews | Public student reviews for Natural Language Processing, including feedback on assignments, course structure, workload, and relevance to AI/LLM interests. | https://www.omscentral.com/courses/natural-language-processing/reviews |


---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
500 characters
**Overlap:**
50 characters
**Reasoning:**
I set it to 500 characters to account for the character size of reviews (since this corpus is made up of student course reviews). I found that they can be as little is 180 and up to 500. I find that 
the size of 500 makes the chunk size small enough to not include too much unrelated context from multiple reviews, but large enough to preserve the main idea of a student comment. I used an overlap of 50 characters to reduce the chance of losing meaning from chunking when breaking in the middle of a sentence.

In addition to fixed-size review text chunks, I will create one synthetic `course_facts` chunk per course. This chunk stores structured course metadata such as course code, credit hours, average rating, average difficulty, and average workload. These fact chunks help the retriever answer factual and comparison questions more reliably.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
sentence-transformers (all-MiniLM-L6-v2)

**Production tradeoff reflection:**
I am using the current model above because it is lightweight, fast, and practical for this small class project. I retrieve the top 3 most similar chunks for each query. This is so the system has enough context to answer without including too much unrelated review text.

If this were deployed for real users and cost is not a constraint, I'd consider using stronger embedding models with better semantic accuracy, longer context support, and stronger performance on education/course-review text. I would also consider increasing top-k or adding a reranking step so the system can retrieve more candidate chunks first and then choose the most relevant ones. The tradeoff would be better answer quality and recall versus higher latency, more compute cost, and more complexity.

The vector store includes both `review_text` chunks and `course_facts` chunks. The `course_facts` chunks support factual lookup and comparison questions, while the `review_text` chunks support summary questions about student experiences.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

I need you to follow these directions along with the diagram as a guide. Use what is in planning.md. I will give another set of instructions after this:

Use your planning.md and pipeline diagram to prompt an AI
tool to generate the generation and interface code. Your prompt should
include: your grounding requirement (answers from retrieved context
only, with source attribution), the output format you want (answer +
source list), and the Gradio skeleton structure if you're using it. Ask
the AI to wire it all together. Before running the generated code, read
through it — make sure the system prompt actually enforces grounding,
not just suggests it, and that source attribution is programmatically
guaranteed rather than left to the LLM to add on its own.

+------------------------+
| 1. Document Ingestion  |
|------------------------|
| Tool: Python           |
| Sources: OMSCentral    |
| Input: 10 course URLs  |
| Output: raw page text  |
+-----------+------------+
            |
            v
+----------------------------+
| 2. Cleaning / Preprocessing|
|----------------------------|
| Tool: Python text cleanup  |
| Remove navigation text,    |
| extra whitespace, headers, |
| footers, and repeated UI   |
| text when possible.        |
| Output: cleaned documents  |
+-----------+----------------+
            |
            v
+------------------------+
| 3. Chunking            |
|------------------------|
| Tool: custom Python    |
| chunking function      |
| Chunk size: 500 chars  |
| Overlap: 50 chars      |
| Output: text chunks,   |
| course_facts chunks    |
| with source metadata   |
+-----------+------------+
            |
            v
+-----------------------------------+
| 4. Embeddings                     |
|-----------------------------------|
| Tool: sentence-transformers       |
| Model: all-MiniLM-L6-v2           |
| Runs locally                      |
| No API key required               |
| No external rate limits           |
|                                   |
| Input: cleaned text chunks        |
| Output: embedding vectors         |
+-----------+-----------------------+
            |
            v
+-----------------------------------+
| 5. Vector Store                   |
|-----------------------------------|
| Tool: ChromaDB                    |
| Runs locally                      |
| No account needed                 |
|                                   |
| Store each chunk with:            |
| - embedding vector                |
| - course/source name              |
| - source URL                      |
| - chunk text                      |    
| - chunk type                      |
|                                   |
| Output: searchable vector index   |
+-----------+-----------------------+
            |
            v
+-----------------------------+
| 6. Retrieval                |
|-----------------------------|
| Tool: ChromaDB similarity   |
| search                      |
| Process:                    |
| - embed user question using |
|   all-MiniLM-L6-v2          |
| - compare question vector   |
|   to stored chunk vectors   |
| - retrieve top-k chunks     |
| Top-k: 5                    |
| Output: most relevant       |
| course review chunks        |
+-----------+-----------------+
            |
            v
+-----------------------------+
| 7. Generation               |
|-----------------------------|
| Tool: Groq API              |
| LLM: llama-3.3-70b-versatile|
| Plan: Free tier             |
| Input: user question +      |
| retrieved chunks            |
| Output: answer grounded in  |
| the retrieved OMSCentral    |
| course review content       |
+-----------------------------+

**How source attribution is surfaced in the response:**

Source attribution is not left to the LLM to add—it is programmatically guaranteed. After retrieval and reranking, the system extracts source metadata (course name, chunk type, and source URL) directly from the retrieved chunks using the _build_source_items() function. These sources are deduplicated and formatted as a markdown list in the format:

1. [Course Name] | [chunk_type] | [source_url]
2. [Course Name] | [chunk_type] | [source_url]

Sources are returned separately from the answer text in the Gradio UI—answers appear in a text box, while sources appear in a dedicated markdown section below. This separation ensures users can clearly see both the answer and its retrieval provenance. Because sources come directly from the metadata of chunks actually used to generate the answer, they reflect the true context the LLM received, eliminating the risk of invented or inaccurate citations.
---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What credit hours are listed for Introduction to Computer Vision and what is it listed as? |Introduction to Computer Vision is listed as CS-6476 and has 3 credit hours. | The credit hours listed for Introduction to Computer Vision are 3, and it is listed as CS-6476. | Accurate | Relevant |
| 2 |According to recent student review content, what is one common warning about Human-Computer Interaction? | Students warn that HCI involves a lot of reading and writing, can include busy work, and may have uneven workload across phases, so it should not be treated as a low-effort class. | One common warning is that it involves substantial reading and writing, and the workload can feel uneven across phases, so the course should not be treated as low-effort. | Accurate | Relevant 
| 3 | What textbook is listed for Natural Language Processing? | Natural Language Processing (2018) by Jacob Eisenstein. | Natural Language Processing (2018) by Jacob Eisenstein. | Accurate | Relevant |
| 4 | What is the average difficulty and average workload for Introduction to Graduate Algorithms? | Introduction to Graduate Algorithms has a 4.05 / 5 difficulty rating and an average workload of 19.20 hrs/week. | The average difficulty for Introduction to Graduate Algorithms is 4.05 / 5 and the average workload is 19.13 hours / week. | Accurate | Relevant |
| 5 | Is Introduction to Graduate Algorithms or AI, Ethics, and Society harder? | Introduction to Graduate Algorithms is the harder course at 4.05 / 5 difficulty | I don't have enough information in the retrieved OMSCentral context to answer that. | Off-target | Inaccurate

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
Is Introduction to Graduate Algorithms or AI, Ethics, and Society harder? 

**What the system returned:**
I don't have enough information in the retrieved OMSCentral context to answer that.

**Root cause (tied to a specific pipeline stage):**
So there is a primary deterministic failure in the generation stage of the pipeline. There is no way to compare easier/harder, but there is a workload comparison path. It would need to use chunk_type=course_facts to check if a course or two courses are easier/harder. It also allows for the comparison of two courses. If there are more than two courses, it will follow the non-deterministic flow of using the LLM.

**What you would change to fix it:**
Add a path in the deterministic logic that allows a comparison path to recognize harder/easier questions that utilizes chunk_type=course_factsto help determine difficulty.
---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
The diagram in the architecture section helped me better imagine the steps in the RAG pipeline.

**One way your implementation diverged from the spec, and why:**
I do not mention that I changed the similirity used by the vector index to compare embeddings from Euclidean distance (L2) to cosine similarity. I did that to improve the distance numbers for the chunks I was getting from top-k.
---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
I asked it to generate the code for embedding and retrieval. I gave it the instructions from the Retrieval Portion of the "Retrieval Approach" section

- *What it produced:*

It produced the code responsible for making each chunk into a numeric embedding that is stored in ChromaDB as vactors. The query is also turned into a numeric embedding that is also stored as a vector. Similarity search is used to determine which vectors best match the query vector using a distance algorithm (cosine similarity in this case). Then the closest top-k results are returned (retrieved context).

- *What I changed or overrode:*

I changed the top-k default value from the original value of 5 to 8.

**Instance 2**

- *What I gave the AI:*
I asked it to create code that produces an interface that asks a user for a prompt in a text box and generates an answer in a text box. I asked it to look at architecture diagram in planning.md as a guide. I also asked it to generate grounded responses only from retrieved documents I specified.

- *What it produced:*
It produced an interface with a text box for user prompts and a text box for answers for those prompts. Sources for answers are printed below the answer text box. The interface (app) has what is called a "grounded QA assistant" that ensures that answers are created from evidence (retrieved context) and not from general memory.

- *What I changed or overrode:*
The change I overrode here was the removal of the debug text box that displayed the top-k chunks in the interface. I moved that data to the terminal where it is printed for debug purposes.