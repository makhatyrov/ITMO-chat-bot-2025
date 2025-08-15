import asyncio, json, os, re, logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from retriever import search
from recommender import recommend_electives

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("Set BOT_TOKEN in .env"); exit(1)

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

BASE = Path(__file__).parent
SEED = json.load(open(BASE/"data"/"programs_seed.json",encoding="utf-8"))

HELP = (
"Я помогу сравнить магистратуры ИТМО:\n"
"• Искусственный интеллект\n"
"• Управление ИИ‑продуктами (AI Product)\n\n"
"Команды:\n"
"/compare — краткое сравнение\n"
"/plan ai|ai_product — показать инфо по учебному плану (если скачан)\n"
"/ask <вопрос> — ответ по содержимому программ\n"
"/reco — рекомендации по элективам под ваш бэкграунд\n"
)

def allowed_query(q:str)->bool:
    # Принимаем только вопросы о поступлении/учёбе/планах
    allow_kw = ["вступ","экзамен","стоим","оплат","бюдж","план","учеб","предмет","курс","семестр",
                "формат","онлайн","очно","карьера","роль","роля","проекты","стипенд","общежит",
                "компания","партнер","вкр","магистр","магистратур","программа","ai product","искусствен"]
    ql = q.lower()
    return any(k in ql for k in allow_kw)

def get_program(slug:str)->Optional[dict]:
    for p in SEED["programs"]:
        if p["slug"]==slug: return p
    return None

@dp.message(CommandStart())
async def start(m:Message):
    await m.answer("Привет! " + HELP)

@dp.message(Command("help"))
async def help_cmd(m:Message):
    await m.answer(HELP)

@dp.message(Command("compare"))
async def compare(m:Message):
    ai = get_program("ai"); ap = get_program("ai_product")
    txt = (
f"<b>Формат</b>\nAI: {ai['format']}\nAI Product: {ap['format']}\n\n"
f"<b>Длительность</b>\nОбе: 2 года\n\n"
f"<b>Стоимость</b>\nОбе: {ai['tuition_per_year_rub']:,} ₽ / год\n\n"
f"<b>Фокус</b>\nAI: инженерия ML/данных, исследования\nAI Product: менеджмент ИИ‑продуктов + техбаза\n\n"
f"<b>Карьерные роли</b>\nAI: {', '.join(ai['career_roles'])}\nAI Product: {', '.join(ap['career_roles'])}\n"
    )
    await m.answer(txt)

@dp.message(Command("plan"))
async def plan_cmd(m:Message):
    parts = m.text.strip().split()
    if len(parts)<2 or parts[1] not in ("ai","ai_product"):
        await m.answer("Использование: /plan ai  или  /plan ai_product")
        return
    slug = parts[1]
    # Если JSON из распарсенного плана существует — отдадим краткую сводку
    jpath = BASE/"plans"
    files = list(jpath.glob(f"{slug}_*.json"))
    pdfs = list(jpath.glob(f"{slug}_*.pdf"))
    if files:
        await m.answer(f"Нашёл распарсенный план: {files[0].name}. Таблицы выгружены как CSV рядом с ним.")
    elif pdfs:
        await m.answer(f"PDF плана скачан ({pdfs[0].name}), но ещё не распаршен. Запустите парсер повторно.")
    else:
        await m.answer("Учебный план пока не скачан. Запустите: python scraper.py или playwright_click.py")

@dp.message(Command("ask"))
async def ask_cmd(m:Message):
    q = m.text.partition(" ")[2].strip()
    if not q:
        await m.answer("Напишите вопрос после команды: /ask какой формат обучения?")
        return
    if not allowed_query(q):
        await m.answer("Отвечаю только на вопросы по обучению/поступлению для двух программ ИТМО.")
        return
    hits = search(q, topk=3)
    if not hits:
        await m.answer("В фактах ИТМО по этой теме ничего не нашёл. Уточните формулировку по поступлению/учёбе.")
        return
    # Собираем факты из seed
    facts = []
    for pid,_ in hits:
        p = get_program(pid)
        if not p: continue
        facts.append(f"🔹 <b>{p['title']}</b>: " + "; ".join(p.get("notes",[])))
    await m.answer("\n".join(facts))

@dataclass
class Profile:
    math:str="mid"
    coding:str="junior"
    product:str="junior"
    goals:list=None

profiles = {}

@dp.message(Command("reco"))
async def reco_cmd(m:Message):
    # простой state: одна строка анкеты
    await m.answer("Опишите через запятую: math=[low|mid|high], coding=[none|junior|mid|senior], product=[none|junior|mid|senior], goals=[ml_engineer|data_engineer|product_manager|data_analyst|ai_research], program=[ai|ai_product]\n\nПример:\nmath=mid, coding=junior, product=mid, goals=product_manager;data_analyst, program=ai_product")

@dp.message(F.text.regexp(r"math\s*=\s*(low|mid|high)"))
async def reco_parse(m:Message):
    s = m.text.lower()
    def grab(key, choices):
        m_ = re.search(key+r"\s*=\s*([a-z_ ;]+)", s)
        if not m_: return None
        val = m_.group(1).strip()
        if key=="goals":
            return [x for x in re.split(r"[;, ]+", val) if x]
        return val if val in choices else None
    math = grab("math", ["low","mid","high"]) or "mid"
    coding = grab("coding", ["none","junior","mid","senior"]) or "junior"
    product = grab("product", ["none","junior","mid","senior"]) or "junior"
    goals = grab("goals", []) or []
    program = grab("program", ["ai","ai_product"]) or "ai_product"
    bg = {"math":math,"coding":coding,"product":product,"goals":goals}
    recs = recommend_electives(bg, program)
    if not recs:
        await m.answer("На основе ваших вводных рекомендаций по элективам не нашлось.")
    else:
        await m.answer("<b>Рекомендованные элективы</b> для " + program + ":\n• " + "\n• ".join(recs))

async def main():
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
