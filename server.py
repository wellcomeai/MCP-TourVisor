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

# ==== НОВЫЕ ENDPOINTS ДЛЯ ПОИСКА ====

@app.post("/find_city")
async def find_city(request: Request):
    """
    Найти город по названию
    Возвращает код города для использования в поиске
    """
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
    """
    Найти страну по названию
    Возвращает код страны для использования в поиске
    """
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

# ==== СУЩЕСТВУЮЩИЕ ENDPOINTS ====

# GET версия (для curl и браузера)
@app.get("/get_references")
async def get_references_get(
    ref_type: str,
    country_code: int = None,
    departure_code: int = None
):
    """
    Получить справочники (GET)
    ref_type: departure, country, region, meal, stars, operator, hotel
    """
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

# POST версия (универсальная для ProTalk и обычных запросов)
@app.post("/get_references")
async def get_references_post(request: Request):
    """
    Получить справочники (POST) - универсальный
    """
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
    """Поиск туров (универсальный)"""
    try:
        data = await extract_params(request)
        
        # Проверяем обязательные параметры
        if "departure" not in data or "country" not in data:
            raise HTTPException(
                status_code=400, 
                detail="departure and country are required"
            )
        
        # Убираем None значения
        params = {k: v for k, v in data.items() if v is not None}
        
        result = await client.search_tours(params)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/actualize_tour")
async def actualize_tour(request: Request):
    """Актуализация тура (универсальная)"""
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
    """Детальная информация о туре (универсальная)"""
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
    """Информация об отеле (универсальная)"""
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
    """Горящие туры (универсальные)"""
    try:
        data = await extract_params(request)
        
        if "city" not in data or "items" not in data:
            raise HTTPException(
                status_code=400, 
                detail="city and items are required"
            )
        
        # Убираем None значения
        params = {k: v for k, v in data.items() if v is not None}
        
        result = await client.get_hot_tours(params)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Для Render нужно указать порт
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
