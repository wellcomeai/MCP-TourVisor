import httpx
import asyncio
from typing import Optional, Dict, Any

class TourVisorClient:
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.base_url = "http://tourvisor.ru/xml"
        
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """Базовый метод для запросов"""
        params["authlogin"] = self.login
        params["authpass"] = self.password
        params["format"] = "json"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
    
    async def get_references(self, ref_type: str, **kwargs) -> Dict:
        """Получить справочники"""
        params = {"type": ref_type, **kwargs}
        return await self._make_request("list.php", params)
    
    async def search_tours(self, params: Dict) -> Dict:
        """Поиск туров (асинхронный)"""
        # Шаг 1: Создаем запрос
        search_response = await self._make_request("search.php", params)
        request_id = search_response.get("requestid")
        
        if not request_id:
            return {"error": "Не получен ID запроса"}
        
        # Шаг 2: Ждем результаты
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(3 if attempt == 0 else 2)
            
            status_params = {
                "requestid": request_id,
                "type": "status"
            }
            status_response = await self._make_request("result.php", status_params)
            status = status_response.get("status", {})
            
            # Если завершен или прошло >7 сек
            if status.get("state") == "finished" or status.get("timepassed", 0) > 7:
                break
            
            attempt += 1
        
        # Шаг 3: Получаем результаты
        result_params = {
            "requestid": request_id,
            "type": "result",
            "page": 1,
            "onpage": 10
        }
        return await self._make_request("result.php", result_params)
    
    async def actualize_tour(self, tourid: str, currency: int = 0) -> Dict:
        """Актуализация тура (проверка цены)"""
        params = {
            "tourid": tourid,
            "currency": currency
        }
        return await self._make_request("actualize.php", params)
    
    async def get_tour_details(self, tourid: str, currency: int = 0) -> Dict:
        """Детальная актуализация (перелеты + доплаты)"""
        params = {
            "tourid": tourid,
            "currency": currency
        }
        return await self._make_request("actdetail.php", params)
    
    async def get_hotel_info(self, hotelcode: int, reviews: int = 0, imgbig: int = 1) -> Dict:
        """Информация об отеле"""
        params = {
            "hotelcode": hotelcode,
            "reviews": reviews,
            "imgbig": imgbig
        }
        return await self._make_request("hotel.php", params)
    
    async def get_hot_tours(self, params: Dict) -> Dict:
        """Горящие туры"""
        return await self._make_request("hottours.php", params)
