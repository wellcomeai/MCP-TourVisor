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
    
    async def find_city(self, city_name: str) -> Dict:
        """Найти город по названию"""
        # Получаем все города
        all_cities = await self.get_references("departure")
        
        # Ищем нужный город (регистронезависимо)
        city_name_lower = city_name.lower().strip()
        
        departures = all_cities.get("lists", {}).get("departures", {}).get("departure", [])
        
        # Поиск по точному совпадению
        for city in departures:
            if city.get("name", "").lower() == city_name_lower:
                return {
                    "found": True,
                    "city": {
                        "id": int(city.get("id")),
                        "name": city.get("name"),
                        "name_from": city.get("namefrom")
                    }
                }
        
        # Поиск по частичному совпадению
        matches = []
        for city in departures:
            if city_name_lower in city.get("name", "").lower():
                matches.append({
                    "id": int(city.get("id")),
                    "name": city.get("name"),
                    "name_from": city.get("namefrom")
                })
        
        if matches:
            return {
                "found": True,
                "city": matches[0],  # Берем первое совпадение
                "alternatives": matches[1:5] if len(matches) > 1 else []  # До 4 альтернатив
            }
        
        return {
            "found": False,
            "message": f"Город '{city_name}' не найден",
            "suggestion": "Попробуйте другое название или уточните"
        }
    
    async def find_country(self, country_name: str) -> Dict:
        """Найти страну по названию"""
        # Получаем все страны
        all_countries = await self.get_references("country")
        
        country_name_lower = country_name.lower().strip()
        
        countries = all_countries.get("lists", {}).get("countries", {}).get("country", [])
        
        # Поиск по точному совпадению
        for country in countries:
            if country.get("name", "").lower() == country_name_lower:
                return {
                    "found": True,
                    "country": {
                        "id": int(country.get("id")),
                        "name": country.get("name")
                    }
                }
        
        # Поиск по частичному совпадению
        matches = []
        for country in countries:
            if country_name_lower in country.get("name", "").lower():
                matches.append({
                    "id": int(country.get("id")),
                    "name": country.get("name")
                })
        
        if matches:
            return {
                "found": True,
                "country": matches[0],
                "alternatives": matches[1:5] if len(matches) > 1 else []
            }
        
        return {
            "found": False,
            "message": f"Страна '{country_name}' не найдена"
        }
    
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
