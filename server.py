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
            "/search_tours_smart",
            "/get_hot_tours_smart",
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

@app.post("/search_tours_smart")
async def search_tours_smart(request: Request):
    """Умный поиск туров - находит коды и ищет туры за один вызов"""
    try:
        data = await extract_params(request)
        
        city_name = data.get("city_name") or data.get("city")
        country_name = data.get("country_name") or data.get("country")
        
        if not city_name or not country_name:
            raise HTTPException(
                status_code=400, 
                detail="city_name and country_name are required"
            )
        
        search_params = {
            k: v for k, v in data.items() 
            if k not in ["city_name", "country_name", "city", "country"] and v is not None
        }
        
        result = await client.search_tours_smart(city_name, country_name, search_params)
        return result
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_hot_tours_smart")
async def get_hot_tours_smart(request: Request):
    """Умный поиск горящих туров - находит коды и ищет горящие туры"""
    try:
        data = await extract_params(request)
        
        city_name = data.get("city_name") or data.get("city")
        
        if not city_name:
            raise HTTPException(
                status_code=400, 
                detail="city_name is required"
            )
        
        # Опциональные страны (может быть список или одна)
        countries_param = data.get("countries") or data.get("country_name") or data.get("country")
        
        # Остальные параметры
        hot_params = {
            k: v for k, v in data.items() 
            if k not in ["city_name", "city", "countries", "country_name", "country"] and v is not None
        }
        
        result = await client.get_hot_tours_smart(city_name, countries_param, hot_params)
        return result
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    """Детальная информация о туре"""
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
    """Горящие туры (с кодами)"""
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
