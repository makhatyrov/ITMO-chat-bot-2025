# Rule-based elective recommendations based on user background.
from typing import List, Dict

def recommend_electives(background:Dict, program_slug:str)->List[str]:
    """
    background: {
      "math": "low|mid|high",
      "coding": "none|junior|mid|senior",
      "product": "none|junior|mid|senior",
      "goals": ["ml_engineer","product_manager","data_analyst","ai_research"]
    }
    """
    recs = []
    if program_slug=="ai":
        if background.get("math","mid") in ("low","mid"):
            recs += ["Линейная алгебра для ML (bridge)",
                     "Математический анализ для ML (интенсив)"]
        if background.get("coding","none") in ("none","junior"):
            recs += ["Python for Data/ML (интенсив)", "Алгоритмы и структуры данных (практикум)"]
        if "ml_engineer" in background.get("goals",[]):
            recs += ["Глубокое обучение", "MLOps и продакшен ML", "Генеративные модели", "Системы рекомендаций"]
        if "data_engineer" in background.get("goals",[]):
            recs += ["Data Warehousing", "Spark/Distributed ML", "Streaming & Kafka"]
        if "ai_research" in background.get("goals",[]):
            recs += ["Оптимизация в ML", "Байесовские методы", "Нейросетевые архитектуры (Advanced)"]
    elif program_slug=="ai_product":
        if background.get("product","none") in ("none","junior"):
            recs += ["Product Management Fundamentals", "Дизайн‑мышление и CustDev"]
        if background.get("coding","none") in ("none","junior"):
            recs += ["Python for Analytics", "SQL для продуктовых аналитиков"]
        if "product_manager" in background.get("goals",[]):
            recs += ["Unit‑экономика (ARPU, LTV, CAC, ROMI)", "A/B‑тестирование и каузальный ин‑френс",
                     "Продуктовый Discovery", "Дорожные карты и приоритизация (RICE, WSJF)"]
        if "data_analyst" in background.get("goals",[]):
            recs += ["Эксперименты и статистика", "BI‑инструменты (Power BI / Tableau)", "Фреймворки принятия решений"]
        if "ml_engineer" in background.get("goals",[]):
            recs += ["ML for PMs (overview)", "GenAI в продуктах: LLM + RAG (практикум)"]
    # Deduplicate while preserving order
    seen=set(); final=[]
    for x in recs:
        if x not in seen:
            seen.add(x); final.append(x)
    return final

if __name__=="__main__":
    demo = {"math":"mid","coding":"junior","product":"mid","goals":["product_manager","data_analyst"]}
    print(recommend_electives(demo, "ai_product"))
