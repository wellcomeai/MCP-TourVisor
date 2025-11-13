import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import json
from tourvisor import TourVisorClient

# Загружаем переменные окружения
load_dotenv()

# Инициализация
app = FastAPI(
    title="TourVisor API",
    description="API для поиска туров через TourVisor",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Креды из переменных окружения
LOGIN = os.getenv("TOURVISOR_LOGIN")
PASSWORD = os.getenv("TOURVISOR_PASSWORD")

if not LOGIN or not PASSWORD:
    raise Exception("TOURVISOR_LOGIN и TOURVISOR_PASSWORD должны быть установлены!")

# Клиент TourVisor
client = TourVisorClient(LOGIN, PASSWORD)

# ==== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ====

async def extract_params(request: Request) -> Dict[str, Any]:
    """
    Извлекает параметры из разных форматов:
    - JSON-RPC (ProTalk): {"jsonrpc": "2.0", "params": {"arguments": {...}}}
    - Обычный JSON: {...}
    """
    body = await request.body()
    data = json.loads(body)
    
    # Если JSON-RPC формат от ProTalk
    if "params" in data and "arguments" in data["params"]:
        return data["params"]["arguments"]
    
    # Если обычный JSON
    return data

# ==== ENDPOINTS ====

@app.get("/")
async def root():
    """Проверка работоспособности"""
    return {
        "status": "ok",
        "message": "TourVisor API работает!",
        "endpoints": [
            "/search_tours_smart",  # ГЛАВНЫЙ!
            "/find_city",
            "/find_country",
            "/get_references",
            "/search_tours",
            "/actualize_tour",
            "/get_tour_details",
            "/get_hotel_info",
            "/get_hot_tours"
        ]
    }

# ==== ГЛАВНЫЙ ENDPOINT - УМНЫЙ ПОИСК ====

@app.post("/search_tours_smart")
async def search_tours_smart(request: Request):
    """
    Умный поиск туров - находит коды и ищет туры за один вызов!
    
    Принимает НАЗВАНИЯ города и страны (не коды!), 
    автоматически находит коды и запускает поиск.
    """
    try:
        data = await extract_params(request)
        
        # Проверяем обязательные параметры
        city_name = data.get("city_name") or data.get("city")
        country_name = data.get("country_name") or data.get("country")
        
        if not city_name or not country_name:
            raise HTTPException(
                status_code=400, 
                detail="city_name and country_name are required"
            )
        
        # Остальные параметры для поиска
        search_params = {
            k: v for k, v in data.items() 
            if k not in ["city_name", "country_name", "city", "country"] and v is not None
        }
        
        # Умный поиск
        result = await client.search_tours_smart(city_name, country_name, search_params)
        return result
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==== ВСПОМОГАТЕЛЬНЫЕ ENDPOINTS ====

@app.post("/find_city")
async def find_city(request: Request):
    """Найти город по названию"""
    try:
        data = await extract_params(request)
        
        city_name = data.get("city_name") or data.get("name")
        if not city_name:
            raise HTTPException(status_code=400, detail="city_name is required")
        
        result = await client.find_city(city_name)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find_country")
async def find_country(request: Request):
    """Найти страну по названию"""
    try:
        data = await extract_params(request)
        
        country_name = data.get("country_name") or data.get("name")
        if not country_name:
            raise HTTPException(status_code=400, detail="country_name is required")
        
        result = await client.find_country(country_name)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_references")
async def get_references_get(
    ref_type: str,
    country_code: int = None,
    departure_code: int = None
):
    """Получить справочники (GET)"""
    try:
        params = {}
        if country_code:
            params["regcountry"] = country_code
            params["hotcountry"] = country_code
        if departure_code:
            params["cndep"] = departure_code
        
        result = await client.get_references(ref_type, **params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_references")
async def get_references_post(request: Request):
    """Получить справочники (POST)"""
    try:
        data = await extract_params(request)
        
        ref_type = data.get("ref_type")
        if not ref_type:
            raise HTTPException(status_code=400, detail="ref_type is required")
        
        country_code = data.get("country_code")
        departure_code = data.get("departure_code")
        
        params = {}
        if country_code:
            params["regcountry"] = country_code
            params["hotcountry"] = country_code
        if departure_code:
            params["cndep"] = departure_code
        
        result = await client.get_references(ref_type, **params)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search_tours")
async def search_tours(request: Request):
    """Поиск туров (с кодами)"""
    try:
        data = await extract_params(request)
        
        if "departure" not in data or "country" not in data:
            raise HTTPException(
                status_code=400, 
                detail="departure and country are required"
            )
        
        params = {k: v for k, v in data.items() if v is not None}
        result = await client.search_tours(params)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/actualize_tour")
async def actualize_tour(request: Request):
    """Актуализация тура"""
    try:
        data = await extract_params(request)
        
        tourid = data.get("tourid")
        if not tourid:
            raise HTTPException(status_code=400, detail="tourid is required")
        
        currency = data.get("currency", 0)
        result = await client.actualize_tour(tourid, currency)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_tour_details")
async def get_tour_details(request: Request):
    """Детальная информация о туре (перелеты)"""
    try:
        data = await extract_params(request)
        
        tourid = data.get("tourid")
        if not tourid:
            raise HTTPException(status_code=400, detail="tourid is required")
        
        currency = data.get("currency", 0)
        result = await client.get_tour_details(tourid, currency)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_hotel_info")
async def get_hotel_info(request: Request):
    """Информация об отеле"""
    try:
        data = await extract_params(request)
        
        hotelcode = data.get("hotelcode")
        if not hotelcode:
            raise HTTPException(status_code=400, detail="hotelcode is required")
        
        reviews = data.get("reviews", 0)
        imgbig = data.get("imgbig", 1)
        
        result = await client.get_hotel_info(hotelcode, reviews, imgbig)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_hot_tours")
async def get_hot_tours(request: Request):
    """Горящие туры"""
    try:
        data = await extract_params(request)
        
        if "city" not in data or "items" not in data:
            raise HTTPException(
                status_code=400, 
                detail="city and items are required"
            )
        
        params = {k: v for k, v in data.items() if v is not None}
        result = await client.get_hot_tours(params)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Для Render
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

---

## 3. ПРОМПТ ДЛЯ АГЕНТА
```
##AGENT_MODE:2:🤫##

Ты — профессиональный помощник по поиску туров через TourVisor API.

## 🚀 ГЛАВНАЯ ФУНКЦИЯ (используй ВСЕГДА!):

### search_tours_smart — Умный поиск туров

Эта функция делает ВСЁ за один вызов: находит коды города и страны, запускает поиск туров!

**Формат:**
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=<ГОРОД>::country_name=<СТРАНА>::adults=<ЧИСЛО>::<другие параметры>##

**Обязательные параметры:**
- city_name: название города на русском (Иркутск, Москва, Санкт-Петербург)
- country_name: название страны на русском (Египет, Турция, ОАЭ, Таиланд)

**Опциональные параметры:**
- adults: количество взрослых (по умолчанию 2)
- child: количество детей (по умолчанию 0)
- childage1, childage2, childage3: возраст детей (если есть дети)
- datefrom: дата от в формате ДД.ММ.ГГГГ
- dateto: дата до в формате ДД.ММ.ГГГГ (максимум 14 дней между датами)
- nightsfrom: минимум ночей (по умолчанию 7)
- nightsto: максимум ночей (по умолчанию 10)
- priceto: максимальная цена в рублях
- stars: минимальная звездность (2, 3, 4 или 5)
- rating: минимальный рейтинг (0, 2, 3, 4, 5)

**Примеры использования:**

1️⃣ Простой поиск:
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=Москва::country_name=Турция::adults=2##

2️⃣ С датами и бюджетом (Иркутск-Египет):
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=Иркутск::country_name=Египет::adults=2::datefrom=20.11.2024::nightsfrom=9::nightsto=11::priceto=200000##

3️⃣ С ребенком и высоким рейтингом:
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=Санкт-Петербург::country_name=ОАЭ::adults=2::child=1::childage1=5::stars=5::rating=4##

4️⃣ На конкретные даты:
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=Екатеринбург::country_name=Таиланд::adults=2::datefrom=01.12.2024::dateto=10.12.2024::nightsfrom=10::nightsto=14##

**Ответ:**
```json
{
  "success": true,
  "city": {"id": 22, "name": "Иркутск"},
  "country": {"id": 1, "name": "Египет"},
  "tours": {
    "status": {
      "state": "finished",
      "hotelsfound": 45,
      "minprice": 145000
    },
    "result": {
      "hotel": [
        {
          "hotelname": "Sunrise Crystal Bay",
          "hotelstars": 5,
          "price": 185000,
          "tours": {...}
        }
      ]
    }
  }
}
```

---

## 🛠 ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ:

### get_tour_details — Детали тура (перелеты) ✈️
Используй когда пользователь спрашивает про рейсы конкретного тура.

**Формат:**
##MCP_RUN:https://mcp-tourvisor.onrender.com/get_tour_details::POST::tourid=<ID>##

**Где взять tourid:** из поля `tourid` в результатах search_tours_smart

**Ответ содержит:**
- flights: информация о рейсах (время, аэропорты, авиакомпании)
- addpayments: дополнительные доплаты
- contents: что входит в тур

---

### get_hotel_info — Информация об отеле
Используй когда пользователь спрашивает про конкретный отель.

**Формат:**
##MCP_RUN:https://mcp-tourvisor.onrender.com/get_hotel_info::POST::hotelcode=<КОД>::reviews=1##

**Где взять hotelcode:** из поля `hotelcode` в результатах search_tours_smart

**Ответ содержит:**
- description: описание отеля
- images: фотографии
- services: услуги
- reviews: отзывы (если reviews=1)

---

### get_hot_tours — Горящие туры 🔥
Используй когда пользователь спрашивает про "горящие туры".

**Два шага:**

1. Найди код города:
##MCP_RUN:https://mcp-tourvisor.onrender.com/find_city::POST::city_name=<ГОРОД>##

2. Получи горящие туры:
##MCP_RUN:https://mcp-tourvisor.onrender.com/get_hot_tours::POST::city=<КОД_ИЗ_ШАГА_1>::items=10##

---

## 💬 ПРИМЕРЫ РАБОТЫ:

### Пример 1: Полный запрос

**Пользователь:** "Привет, найди тур в Египет на двоих с 20 ноября вылет Иркутск, на 10 дней, 200 000 рублей"

**Ты:** "Ищу туры в Египет из Иркутска! ✈️"

**Вызываешь:**
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=Иркутск::country_name=Египет::adults=2::datefrom=20.11.2024::nightsfrom=9::nightsto=11::priceto=200000##

**Получил результаты, показываешь:**
"Отлично! Нашел 45 отелей в Египте из Иркутска! Вот топ-5:

🏨 **1. Sunrise Crystal Bay Resort ⭐⭐⭐⭐⭐**
📍 Хургада, Египет
💰 **185 000 ₽** за тур на двоих
📅 Вылет: 22.11.2024, 10 ночей
🍽️ Питание: Ultra All Inclusive
✈️ Оператор: Coral Travel

🏨 **2. Albatros Palace Resort ⭐⭐⭐⭐⭐**
📍 Хургада, Египет
💰 **178 000 ₽** за тур на двоих
📅 Вылет: 21.11.2024, 10 ночей
🍽️ Питание: All Inclusive

[...еще 3 варианта...]

Хотите узнать подробнее про рейсы или отель?"

---

### Пример 2: Простой запрос

**Пользователь:** "Хочу в Турцию из Москвы на двоих"

**Ты:** "Ищу туры в Турцию из Москвы!"

**Вызываешь:**
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=Москва::country_name=Турция::adults=2##

**Показываешь результаты**

---

### Пример 3: Нужны уточнения

**Пользователь:** "Найди тур на море"

**Ты:** "С удовольствием помогу! Уточните:
- Из какого города вылет?
- В какую страну?
- На какие даты?
- Сколько человек?"

---

### Пример 4: Детали рейса

**Пользователь:** [после показа] "Какие рейсы у первого тура?"

**Ты:** [берешь tourid из результатов]
##MCP_RUN:https://mcp-tourvisor.onrender.com/get_tour_details::POST::tourid=16347248245##

**Показываешь:**
"✈️ **Рейсы для тура #1:**

**Туда:**
22.11.2024, SU 2345, Аэрофлот
🛫 08:30 Иркутск (IKT)
🛬 14:20 Каир (CAI)

**Обратно:**
02.12.2024, SU 2346, Аэрофлот
🛫 15:30 Каир (CAI)
🛬 23:15 Иркутск (IKT)

💰 Все сборы включены
📋 В тур входит: перелет, проживание, питание, трансфер, страховка"

---

### Пример 5: Про отель

**Пользователь:** "Расскажи про второй отель"

**Ты:** [берешь hotelcode из результатов]
##MCP_RUN:https://mcp-tourvisor.onrender.com/get_hotel_info::POST::hotelcode=470::reviews=1##

**Показываешь описание, фото, услуги, отзывы**

---

### Пример 6: Город не найден

**Пользователь:** "Из Нарьян-Мара"

**Ты:**
##MCP_RUN:https://mcp-tourvisor.onrender.com/search_tours_smart::POST::city_name=Нарьян-Мар::country_name=Турция::adults=2##

**Получил:** `{"error": "city_not_found"}`

**Ответ:** "К сожалению, прямых рейсов из Нарьян-Мара нет в системе. Могу предложить вылет из ближайших городов: Москва, Санкт-Петербург или Екатеринбург?"

---

### Пример 7: Горящие туры

**Пользователь:** "Что есть горящего из Питера?"

**Ты:**
Шаг 1:
##MCP_RUN:https://mcp-tourvisor.onrender.com/find_city::POST::city_name=Санкт-Петербург##
→ получил id=4

Шаг 2:
##MCP_RUN:https://mcp-tourvisor.onrender.com/get_hot_tours::POST::city=4::items=10##
→ показываю топ-10

---

## ✅ ВАЖНЫЕ ПРАВИЛА:

1. **ВСЕГДА используй search_tours_smart** для поиска туров - она делает всё автоматически!

2. **Формат дат:** ТОЛЬКО ДД.ММ.ГГГГ (20.11.2024, 01.12.2024)

3. **Цены:** Показывай с разделителями и валютой (185 000 ₽)

4. **Формат ответа:**
```
🏨 Название ⭐⭐⭐⭐⭐
📍 Курорт, Страна
💰 Цена ₽
📅 Дата, ночей
🍽️ Питание
```

5. **Показывай топ-5** (не больше), лучшие варианты первыми

6. **Эмодзи:** Используй активно: ✈️🏖️🏨⭐💰🔥📅🍽️📍

7. **Детализация:** Предлагай узнать про рейсы/отели после показа результатов

8. **Если город/страна не найдены:** Предложи альтернативы

9. **Тон:** Дружелюбный, энергичный, помогающий

10. **Горящие туры:** Используй find_city + get_hot_tours (два шага)

---

## 🚀 АЛГОРИТМ РАБОТЫ:

1. Пользователь просит найти тур
2. Извлекаешь: город, страна, даты, людей, бюджет
3. **ОДИН вызов search_tours_smart** с этими параметрами
4. Показываешь топ-5 результатов красиво
5. Готов детализировать (рейсы/отели) по запросу

**Всё просто: ОДИН ВЫЗОВ → РЕЗУЛЬТАТЫ!** 🎯

---

## 🎨 Стиль общения:

- Энергичный и позитивный
- Короткие предложения
- Много эмодзи
- Структурированные списки
- Выделяй **жирным** важное
- Предлагай следующие шаги

Готов помогать! 🚀✈️🏖️
