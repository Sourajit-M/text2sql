i am building an multi agent system using langgraph of text to sql with a clarification engine.
i will explain you the entire workflow of the project. but you need to keep certain thing in mind

-- simple file structure and code, dont over engineer
-- i will use uv package manager, for llm will use groq openai/gpt-oss-120b model, for database we will use postgresql but it is not locally installed i will use it through docker

1. the user asks a question, it goes to the intent/ambiguity agent which checks if the question is clear enough
eg: show me the best customer of last month?
what is meant by best - it may be most ordered, most revenue, repeated orders etc

2. if the question was already cleared enough it goes to the sql schema agent.
if the question was not enough containing the information, it goes to the clarification agent
which asks the user with minimal clarification questions needed to know to get a clear result and again after user answers the question it goes to intent / ambiguity agent to know, now if the question is clear not follow same process, but max retries should be 3 times. if still not solved break the program and inform the user

3. the schema agent retrieves relevant columns depending on the context of the question. it solves the problem instead of giving entire database to the sql generator agent. it only gets the relevant columns with the data to the sql generator agent to generate the sql query
eg : which products generated most revenue?
relevant columns : products, order, order_item

4. the sql generator agent produces the query understanding the question and the context of the retrieved columns from the schema agent.

5. the result then flows to the sql validator agent, it checks
the sql syntax, table exist or not, join relations are working fine, user's intent is satisfied properly, any dangerous operations, repeating/ excessive expensive queries.
if something is wrong, it does self correction else it proceeds to execute the query through a SQL execution sandbox, after self correction recheck the entire process so to minimize fault. max retries should 3 times of the entire process of checking if still not solved break the program and inform the user

6. then finally the explanation agent explains the user the results retrieved through executing the query successfully in simple terms

After all this make a pytest testing of the project to get grounded results 
build a small synthetic e-commerce PostgreSQL database for this project
we will have a fastapi layer to run this project, later we will make react front

write the code go phase by phase rather doing everything at once, after each phase give me a git commit message to commit. ask if there are any open questions from your side then ask i will give you some test scenaiors to test later on

TC	Question / Scenario	Expected
TC1	"What is the capital of France?"	END — Unrelated
TC2	"Which products generated the most revenue?"	SUCCESS
TC3	"Who was the best customer last month?" → "Highest revenue"	SUCCESS after clarification
TC4	"Show me sales for last month." → "Total revenue"	SUCCESS after clarification
TC5	"Show me the best products." → User gives unclear answer	Clarify again
TC6	"Who are the best customers?" → User refuses clarification	END — Insufficient information
TC7	SQL uses non-existent column	Self-correct → SUCCESS
TC8	SQL uses non-existent table	Self-correct → SUCCESS
TC9	SQL has incorrect JOIN	Self-correct → SUCCESS
TC10	SQL is valid but doesn't match user intent	Self-correct → SUCCESS
TC11	SQL contains DROP/DELETE/UPDATE	FAIL — Unsafe SQL
TC12	SQL fails twice, succeeds on 3rd attempt	SUCCESS
TC13	SQL fails all 3 attempts	FAIL — Retry exhausted
TC14	Valid SQL but database execution fails	FAIL — Execution error
TC15	Valid query returns no rows	SUCCESS — Empty result
TC16	Query is excessively expensive	Reject / Correct
TC17	Schema retrieval misses required table	Refine schema → SUCCESS
TC18	"Best customer" → revenue/order count changes required schema	Correct schema → SUCCESS

