from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
import os

DB_PATH = "orders.db"
PERSIST_DIR = "./chroma_langchain_db"
API_KEY = "AIzaSyBj9u6pNxU1HHUeF8LGFuygxIogNvRtt00"

# Initialize Chroma vector store
if os.path.exists(PERSIST_DIR):
    vectordb = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=API_KEY
        )
    )
else:
    raise Exception("ChromaDB not found. Run the document embedding process first.")

retriever = vectordb.as_retriever()

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "order" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            std_triangle_code_1 TEXT,
            std_triangle_code_2 TEXT,
            recipe_triangle_code_1 TEXT,
            recipe_triangle_code_2 TEXT,
            recipe_type_code TEXT,
            fastness_type TEXT,
            article_dye_check_result TEXT,
            check_dye_triangle TEXT,
            no_of_stages INTEGER,
            max_recipe_age_in_days INTEGER,
            last_update_date DATE,
            standard_saved_date DATE,
            min_no_of_lots INTEGER,
            max_delta_e REAL,
            max_delta_l REAL,
            max_delta_c REAL,
            max_delta_h REAL,
            no_of_matching_lots INTEGER,
            de_of_average REAL,
            dl_of_average REAL,
            dc_of_average REAL,
            dh_of_average REAL,
            report_analysis TEXT    
        )
    """)
    conn.commit()
    conn.close()
    yield

app = FastAPI(lifespan=lifespan)

class OrderModel(BaseModel):
    std_triangle_code_1: str
    std_triangle_code_2: str
    recipe_triangle_code_1: str
    recipe_triangle_code_2: str
    recipe_type_code: str
    fastness_type: str
    article_dye_check_result: str
    check_dye_triangle: str
    no_of_stages: int
    max_recipe_age_in_days: int
    last_update_date: str
    standard_saved_date: Optional[str] = None
    min_no_of_lots: int
    max_delta_e: float
    max_delta_l: float
    max_delta_c: float
    max_delta_h: float
    no_of_matching_lots: int
    de_of_average: float
    dl_of_average: float
    dc_of_average: float
    dh_of_average: float

@app.get("/get_orders")
def get_orders():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM 'order'")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0]} for row in rows]

@app.get("/process_order/{order_id}")
def process_order(order_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT report_analysis FROM 'order' WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    return {"id": order_id, "report_analysis": row[0]}

@app.post("/add_order")
def add_order(order: OrderModel):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Normalize to string and lowercase for comparison (excluding report_analysis)
    data = order.model_dump()
    normalized = {k: str(v).strip().lower() for k, v in data.items()}

    where_clause = " AND ".join([f"LOWER(TRIM(CAST({k} AS TEXT))) = ?" for k in normalized])
    values = list(normalized.values())

    cursor.execute(f"SELECT id, report_analysis FROM 'order' WHERE {where_clause}", values)
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return {"message": "Order already exist", "order_id": existing[0], "report_analysis": existing[1]}

    report_analysis = process_with_llm(data)
    data["report_analysis"] = report_analysis

    cursor.execute(f"""
        INSERT INTO 'order' ({', '.join(data.keys())})
        VALUES ({', '.join(['?'] * len(data))})
    """, list(data.values()))

    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return {"message": "Order added", "order_id": order_id, "report_analysis": report_analysis}

def process_with_llm(user_inputs):
    today = datetime.today().strftime("%Y-%m-%d")
    related_docs = retriever.invoke(str(user_inputs))
    reference_text = "\n".join([doc.page_content for doc in related_docs])

    prompt = f"""
    You are an expert assistant processing recipe pre-screening. Use the following DOCUMENT as a reference:
    {reference_text}

    Given these user inputs:
    {user_inputs}

    Today's date is {today}.

    Process the inputs according to the steps given in the document and return the result of each step.
    Explain the overall result and list the failure reasons along with the Zone.
    """

    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.3,
        google_api_key=API_KEY
    )
    response = model.invoke(prompt)
    return response.content
