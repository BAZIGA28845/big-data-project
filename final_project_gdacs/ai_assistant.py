import logging
import os

from dotenv import load_dotenv
from groq import Groq

from db import get_connection

load_dotenv()
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

TABLE_SCHEMA = """
Table: clean_gdacs
Columns:
- event_id (integer, unique id for each disaster)
- event_type (text, short code: EQ=earthquake, FL=flood, TC=tropical cyclone, DR=drought, VO=volcano, WF=wildfire)
- event_name (text)
- alert_level (text, either 'Orange' or 'Red')
- alert_score (numeric)
- country (text, country name)
- from_date (timestamp, when the event started)
- to_date (timestamp, when the event ended)
- year (integer)
- latitude (numeric)
- longitude (numeric)
- severity_value (numeric, may be null)
- severity_unit (text, may be null)
- population_value (numeric, population exposed, may be null)
"""

FORBIDDEN_KEYWORDS = ["drop", "delete", "update", "insert", "alter", "truncate", "grant", "revoke"]


class UnsafeQueryError(Exception):
    pass


def question_to_sql(question: str) -> str:
    """
    Sends the user's plain-English question to Groq, asking it to
    return ONLY a SQL SELECT query that answers it against clean_gdacs.
    """
    prompt = f"""You are a SQL expert. Given this table schema:

{TABLE_SCHEMA}

Write a single PostgreSQL SELECT query that answers this question:
"{question}"

Rules:
- Return ONLY the SQL query, no explanation, no markdown formatting, no backticks
- Only use SELECT statements - never modify data
- If the question cannot be answered from this table, return exactly: NO_QUERY
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.strip("`").replace("sql\n", "").strip()
    logger.info(f"Generated SQL: {sql}")
    return sql


def is_safe_select(sql: str) -> bool:
    """Only allow SELECT queries - reject anything that could modify data."""
    lowered = sql.lower().strip()
    if not lowered.startswith("select"):
        return False
    if any(keyword in lowered for keyword in FORBIDDEN_KEYWORDS):
        return False
    return True


def run_sql(sql: str):
    """
    Executes the SQL query and returns the result rows and column
    names. Raises RuntimeError with a clear message if the query
    fails, rather than letting a raw database error propagate.
    """
    if not is_safe_select(sql):
        raise UnsafeQueryError(f"Refused to run unsafe/non-SELECT query: {sql}")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
        return columns, rows
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        raise RuntimeError(f"The query failed to run: {e}") from e


def result_to_sentence(question: str, columns, rows) -> str:
    """
    Sends the SQL result back to Groq and asks it to phrase the
    answer as a plain-English sentence.
    """
    if not rows:
        return "I couldn't find any data matching that question."

    result_text = f"Columns: {columns}\nRows: {rows[:20]}"  # cap rows sent to the AI

    prompt = f"""The user asked: "{question}"

The database returned this result:
{result_text}

Write ONE short, naturally-phrased, grammatically correct sentence that directly answers
the user's question using this data. Rephrase the question's wording naturally rather than
echoing it awkwardly. Do not mention SQL, columns, or databases.

Example of good phrasing: "Indonesia had the most Orange alert events, with 42 recorded."
Example of bad phrasing: "Indonesia experienced more orange."
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def ask(question: str) -> str:
    """
    Full pipeline: question -> SQL -> run query -> plain-English answer.
    Handles failures at each stage gracefully instead of crashing.
    """
    try:
        sql = question_to_sql(question)
    except Exception as e:
        logger.error(f"Failed to generate SQL: {e}")
        return "Sorry, I had trouble understanding that question - could you rephrase it?"

    if sql.strip() == "NO_QUERY":
        return "I don't think I can answer that from this dataset - try asking about disaster type, country, year, or alert level."

    try:
        columns, rows = run_sql(sql)
    except UnsafeQueryError:
        return "Sorry, I can't run that kind of question safely - please rephrase it as a simple data question."
    except RuntimeError:
        return "Sorry, something went wrong trying to look that up. Could you try rephrasing the question?"

    try:
        return result_to_sentence(question, columns, rows)
    except Exception as e:
        logger.error(f"Failed to generate sentence: {e}")
        # fall back to just showing the raw result rather than failing completely
        return f"Here's what I found: {rows[:5]}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("GDACS AI Assistant - ask a question about the disaster data (type 'quit' to exit)\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if not question:
            continue
        answer = ask(question)
        print(f"Assistant: {answer}\n")