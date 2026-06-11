# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

My domain is courses that a Georgia Tech OMSCS student interested in Artificial Intelligence might consider. This project ingests public OMSCentral review pages for Georgia Tech OMSCS courses that are relevant to or commonly considered by students pursuing the Artificial Intelligence specialization. Each course review page is treated as one source document. The guide summarizes student-reported patterns about workload, difficulty, course organization, teaching support, assignments, and perceived usefulness. This project is unofficial and should not be treated as an official Georgia Tech evaluation system. 

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

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

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->


**Chunk size:**
500 characters
**Overlap:**
50 characters
**Reasoning:**
I set it to 500 characters to account for the character size of reviews (since this corpus is made up of student course reviews). I found that they can be as little is 180 and up to 500. I find that 
the size of 500 makes the chunk size small enough to not include too much unrelated context from multiple reviews, but large enough to preserve the main idea of a student comment. I used an overlap of 50 characters to reduce the chance of losing meaning from chunking when breaking in the middle of a sentence.

In addition to fixed-size review text chunks, I will create one synthetic `course_facts` chunk per course. This chunk stores structured course metadata such as course code, credit hours, average rating, average difficulty, and average workload. These fact chunks help the retriever answer factual and comparison questions more reliably.
---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
sentence-transformers (all-MiniLM-L6-v2)

**Top-k:**
3

**Production tradeoff reflection:**
I am using the current model above because it is lightweight, fast, and practical for this small class project. I retrieve the top 3 most similar chunks for each query. This is so the system has enough context to answer without including too much unrelated review text.

If this were deployed for real users and cost is not a constraint, I'd consider using stronger embedding models with better semantic accuracy, longer context support, and stronger performance on education/course-review text. I would also consider increasing top-k or adding a reranking step so the system can retrieve more candidate chunks first and then choose the most relevant ones. The tradeoff would be better answer quality and recall versus higher latency, more compute cost, and more complexity.

The vector store includes both `review_text` chunks and `course_facts` chunks. The `course_facts` chunks support factual lookup and comparison questions, while the `review_text` chunks support summary questions about student experiences.
---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What credit hours are listed for Introduction to Computer Vision and what is it listed as? | Introduction to Computer Vision is listed as CS-6476 and has 3 credit hours. |
| 2 | Which has the higher average workload: Artificial Intelligence or Game Artificial Intelligence? | Artificial Intelligence has the higher average workload: 22.32 hrs/week compared with Game Artificial Intelligence at 11.40 hrs/week. |
| 3 | What textbook is listed for Natural Language Processing? | Natural Language Processing (2018) by Jacob Eisenstein. |
| 4 | What is the average difficulty and average workload for Introduction to Graduate Algorithms? | Introduction to Graduate Algorithms has a 4.05 / 5 difficulty rating and an average workload of 19.20 hrs/week. |
| 5 | According to recent student review content, what is one common warning about Human-Computer Interaction? | Students warn that HCI involves a lot of reading and writing, can include busy work, and may have uneven workload across phases, so it should not be treated as a low-effort class. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Fixed-size character chunking may split key information across important boundaries, such as the middle of a sentence, review, course description, or metadata field. The 50-character overlap helps reduce this risk, but some context could still be separated across chunks.

2. Top-k 3 could potentially miss relevant context, especially if the answer is spread across several reviews or course sections. Retrieving only 3 chunks keeps responses focused, but it may leave out useful supporting information for broader summary or comparison questions.

3. Because the corpus includes both `course_facts` chunks and `review_text` chunks, retrieval may sometimes return the wrong type of chunk for a question. For example, a broad student-experience question should retrieve review text, while a workload comparison question should retrieve course facts. Including a `chunk_type` metadata field can help inspect and debug retrieval results.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

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
| Top-k: 3                    |
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

The pipeline starts by loading public OMSCentral review pages for selected Georgia Tech OMSCS courses. Each page is cleaned to remove unnecessary webpage text and then split into fixed-size chunks using 500-character chunks with 50-character overlap. Each chunk is embedded locally using `sentence-transformers/all-MiniLM-L6-v2`. The resulting vectors and source metadata are stored locally in ChromaDB. When a user asks a question, the app embeds the query with the same embedding model, retrieves the top 3 most similar chunks from ChromaDB, and sends the user question plus retrieved context to Groq using `llama-3.3-70b-versatile` to generate a grounded answer.



---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
