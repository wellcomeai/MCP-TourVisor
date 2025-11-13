import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from tourvisor import TourVisorClient
from models import (
    SearchToursRequest, 
    ActualizeTourRequest, 
    GetHotToursRequest,
    GetHotelInfoRequest
)

# Загружаем переменные окружения
load_dotenv()

# Инициализация
app = FastAPI(
    title="TourVisor API",
    description="API для поиска туров через TourVisor",
    version="1.0.0"
)

# CORS (если нужно)
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

# ==== ENDPOINTS ====

@app.get("/")
async def root():
    """Проверка работоспособности"""
    return {
        "status": "ok",
        "message": "TourVisor API работает!",
        "endpoints": [
            "/get_references",
            "/search_tours",
            "/actualize_tour",
            "/get_tour_details",
            "/get_hotel_info",
            "/get_hot_tours"
        ]
    }

@app.get("/get_references")
async def get_references(
    ref_type: str,
    country_code: int = None,
    departure_code: int = None
):
    """
    Получить справочники
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

@app.post("/search_tours")
async def search_tours(request: SearchToursRequest):
    """Поиск туров"""
    try:
        # Конвертируем в dict, убираем None
        params = {k: v for k, v in request.dict().items() if v is not None}
        result = await client.search_tours(params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/actualize_tour")
async def actualize_tour(request: ActualizeTourRequest):
    """Актуализация тура (проверка цены)"""
    try:
        result = await client.actualize_tour(
            request.tourid,
            request.currency
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_tour_details")
async def get_tour_details(request: ActualizeTourRequest):
    """Детальная информация о туре (перелеты, доплаты)"""
    try:
        result = await client.get_tour_details(
            request.tourid,
            request.currency
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_hotel_info")
async def get_hotel_info(request: GetHotelInfoRequest):
    """Информация об отеле"""
    try:
        result = await client.get_hotel_info(
            request.hotelcode,
            request.reviews,
            request.imgbig
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_hot_tours")
async def get_hot_tours(request: GetHotToursRequest):
    """Горящие туры"""
    try:
        params = {k: v for k, v in request.dict().items() if v is not None}
        result = await client.get_hot_tours(params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Для Render нужно указать порт
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
