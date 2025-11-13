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
        # Создаем КОПИЮ params чтобы не модифицировать оригинал
        request_params = params.copy()
        request_params["authlogin"] = self.login
        request_params["authpass"] = self.password
        request_params["format"] = "json"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/{endpoint}", params=request_params)
            response.raise_for_status()
            return response.json()
    
    async def get_references(self, ref_type: str, **kwargs) -> Dict:
        """Получить справочники"""
        params = {"type": ref_type, **kwargs}
        return await self._make_request("list.php", params)
    
    async def find_city(self, city_name: str) -> Dict:
        """Найти город по названию"""
        all_cities = await self.get_references("departure")
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
                "city": matches[0],
                "alternatives": matches[1:5] if len(matches) > 1 else []
            }
        
        return {
            "found": False,
            "message": f"Город '{city_name}' не найден",
            "suggestion": "Попробуйте другое название или уточните"
        }
    
    async def find_country(self, country_name: str) -> Dict:
        """Найти страну по названию"""
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
    
    def _convert_params(self, params: Dict) -> Dict:
        """Конвертирует строковые параметры в правильные типы"""
        converted = {}
        
        # Числовые параметры
        int_params = [
            'departure', 'country', 'adults', 'child', 
            'childage1', 'childage2', 'childage3',
            'nightsfrom', 'nightsto', 'stars', 'rating',
            'pricefrom', 'priceto', 'currency', 'hotelcode',
            'tourid', 'city', 'items', 'maxdays'
        ]
        
        for key, value in params.items():
            if key in int_params and value is not None:
                try:
                    converted[key] = int(value)
                except (ValueError, TypeError):
                    converted[key] = value
            else:
                converted[key] = value
        
        return converted
    
    async def search_tours(self, params: Dict) -> Dict:
        """Поиск туров (асинхронный)"""
        # Конвертируем параметры
        clean_params = self._convert_params(params)
        
        # Шаг 1: Создаем запрос
        search_response = await self._make_request("search.php", clean_params)
        
        # Проверяем на ошибки
        if "error" in search_response:
            return {"error": search_response.get("error"), "details": search_response}
        
        # ✅ ИСПРАВЛЕНИЕ: API возвращает {"result": {"requestid": "..."}}
        request_id = search_response.get("result", {}).get("requestid")
        
        if not request_id:
            return {
                "error": "Не получен ID запроса",
                "api_response": search_response,
                "sent_params": clean_params
            }
        
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
    
    async def search_tours_smart(self, city_name: str, country_name: str, params: Dict) -> Dict:
        """Умный поиск: находит коды города и страны, затем ищет туры"""
        # Шаг 1: Находим город
        city_result = await self.find_city(city_name)
        if not city_result.get("found"):
            return {
                "error": "city_not_found",
                "message": f"Город '{city_name}' не найден",
                "city_search": city_result
            }
        
        city_id = city_result["city"]["id"]
        
        # Шаг 2: Находим страну
        country_result = await self.find_country(country_name)
        if not country_result.get("found"):
            return {
                "error": "country_not_found",
                "message": f"Страна '{country_name}' не найдена",
                "country_search": country_result
            }
        
        country_id = country_result["country"]["id"]
        
        # Шаг 3: Добавляем коды к параметрам
        search_params = {
            "departure": city_id,
            "country": country_id,
            **params
        }
        
        # Шаг 4: Ищем туры
        tours_result = await self.search_tours(search_params)
        
        # Шаг 5: Возвращаем всё вместе
        return {
            "success": True,
            "city": city_result["city"],
            "country": country_result["country"],
            "search_params": search_params,
            "tours": tours_result
        }
    
    async def actualize_tour(self, tourid: str, currency: int = 0) -> Dict:
        """Актуализация тура (проверка цены)"""
        params = self._convert_params({
            "tourid": tourid,
            "currency": currency
        })
        return await self._make_request("actualize.php", params)
    
    async def get_tour_details(self, tourid: str, currency: int = 0) -> Dict:
        """Детальная актуализация (перелеты + доплаты)"""
        params = self._convert_params({
            "tourid": tourid,
            "currency": currency
        })
        return await self._make_request("actdetail.php", params)
    
    async def get_hotel_info(self, hotelcode: int, reviews: int = 0, imgbig: int = 1) -> Dict:
        """Информация об отеле"""
        params = self._convert_params({
            "hotelcode": hotelcode,
            "reviews": reviews,
            "imgbig": imgbig
        })
        return await self._make_request("hotel.php", params)
    
    async def get_hot_tours(self, params: Dict) -> Dict:
        """Горящие туры"""
        clean_params = self._convert_params(params)
        return await self._make_request("hottours.php", clean_params)
