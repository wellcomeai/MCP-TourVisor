import httpx
import asyncio
from typing import Optional, Dict, Any, List

class TourVisorClient:
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.base_url = "http://tourvisor.ru/xml"
        
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """Базовый метод для запросов с улучшенной обработкой ошибок"""
        request_params = params.copy()
        request_params["authlogin"] = self.login
        request_params["authpass"] = self.password
        request_params["format"] = "json"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.base_url}/{endpoint}", params=request_params)
                
                # Пытаемся распарсить JSON, даже если статус не 200
                try:
                    data = response.json()
                except Exception as json_error:
                    # Если не JSON - возвращаем ошибку с текстом ответа
                    return {
                        "iserror": True,
                        "errormessage": f"API вернул не JSON. Status: {response.status_code}",
                        "response_text": response.text[:500] if response.text else "Empty response"
                    }
                
                # Проверяем статус ответа
                if response.status_code != 200:
                    # API вернул ошибку, но это может быть валидный JSON с iserror
                    if isinstance(data, dict) and data.get("iserror"):
                        return data  # Возвращаем ошибку из API как есть
                    else:
                        return {
                            "iserror": True,
                            "errormessage": f"HTTP {response.status_code}",
                            "response": data
                        }
                
                # Проверяем наличие iserror в успешном ответе
                if isinstance(data, dict) and data.get("iserror"):
                    return data  # Возвращаем ошибку из API
                
                # Всё хорошо - возвращаем данные
                return data
                
            except httpx.TimeoutException:
                return {
                    "iserror": True,
                    "errormessage": "Таймаут запроса к TourVisor API (30 сек)"
                }
            except httpx.ConnectError:
                return {
                    "iserror": True,
                    "errormessage": "Не удалось подключиться к TourVisor API"
                }
            except Exception as e:
                return {
                    "iserror": True,
                    "errormessage": f"Ошибка соединения: {str(e)}"
                }
    
    async def get_references(self, ref_type: str, **kwargs) -> Dict:
        """Получить справочники"""
        params = {"type": ref_type, **kwargs}
        return await self._make_request("list.php", params)
    
    async def find_city(self, city_name: str) -> Dict:
        """Найти город по названию"""
        all_cities = await self.get_references("departure")
        
        # Проверка на ошибку
        if all_cities.get("iserror"):
            return {
                "found": False,
                "error": "api_error",
                "message": all_cities.get("errormessage", "Ошибка получения списка городов")
            }
        
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
        
        # Проверка на ошибку
        if all_countries.get("iserror"):
            return {
                "found": False,
                "error": "api_error",
                "message": all_countries.get("errormessage", "Ошибка получения списка стран")
            }
        
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
    
    async def find_countries(self, country_names: List[str]) -> Dict:
        """Найти несколько стран по названиям"""
        all_countries_response = await self.get_references("country")
        
        if all_countries_response.get("iserror"):
            return {
                "found": False,
                "error": "api_error",
                "message": all_countries_response.get("errormessage", "Ошибка получения списка стран")
            }
        
        countries_data = all_countries_response.get("lists", {}).get("countries", {}).get("country", [])
        
        found_countries = []
        not_found = []
        
        for country_name in country_names:
            country_name_lower = country_name.lower().strip()
            found = False
            
            # Точное совпадение
            for country in countries_data:
                if country.get("name", "").lower() == country_name_lower:
                    found_countries.append({
                        "id": int(country.get("id")),
                        "name": country.get("name")
                    })
                    found = True
                    break
            
            # Частичное совпадение
            if not found:
                for country in countries_data:
                    if country_name_lower in country.get("name", "").lower():
                        found_countries.append({
                            "id": int(country.get("id")),
                            "name": country.get("name")
                        })
                        found = True
                        break
            
            if not found:
                not_found.append(country_name)
        
        if not found_countries:
            return {
                "found": False,
                "message": f"Страны не найдены: {', '.join(not_found)}"
            }
        
        return {
            "found": True,
            "countries": found_countries,
            "not_found": not_found if not_found else None
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
    
    def _flatten_tours(self, search_result: Dict, limit: int = 10) -> List[Dict]:
        """Разворачивает туры из структуры hotels в плоский список
        
        Args:
            search_result: результат поиска от API
            limit: максимальное количество туров (по умолчанию 10, None = все)
        
        Returns:
            Список туров, отсортированный по цене
        """
        flat_tours = []
        
        # Проверяем на ошибку
        if search_result.get("iserror"):
            return []
        
        # Проверяем наличие данных
        hotels = search_result.get("data", {}).get("result", {}).get("hotel", [])
        
        # Если hotels не список, а словарь (один отель), делаем список
        if isinstance(hotels, dict):
            hotels = [hotels]
        
        for hotel in hotels:
            # Информация об отеле
            hotel_info = {
                "hotelcode": hotel.get("hotelcode"),
                "hotelname": hotel.get("hotelname"),
                "hotelstars": hotel.get("hotelstars"),
                "hotelrating": hotel.get("hotelrating"),
                "regionname": hotel.get("regionname"),
                "regioncode": hotel.get("regioncode"),
                "countryname": hotel.get("countryname"),
                "countrycode": hotel.get("countrycode"),
                "hoteldescription": hotel.get("hoteldescription"),
                "picturelink": hotel.get("picturelink"),
                "fulldesclink": hotel.get("fulldesclink"),
                "reviewlink": hotel.get("reviewlink"),
                "seadistance": hotel.get("seadistance"),
                "isphoto": hotel.get("isphoto"),
                "iscoords": hotel.get("iscoords"),
                "isdescription": hotel.get("isdescription"),
                "isreviews": hotel.get("isreviews")
            }
            
            # Получаем туры для этого отеля
            tours_data = hotel.get("tours", {})
            
            # tours может быть словарем с ключом "tour" или сразу списком
            if isinstance(tours_data, dict):
                tours_list = tours_data.get("tour", [])
            else:
                tours_list = tours_data
            
            # Если один тур - делаем список
            if isinstance(tours_list, dict):
                tours_list = [tours_list]
            
            # Разворачиваем все туры из этого отеля
            for tour in tours_list:
                flat_tour = {
                    **hotel_info,  # Добавляем инфо об отеле
                    # Информация о туре
                    "tourid": tour.get("tourid"),
                    "operatorcode": tour.get("operatorcode"),
                    "operatorname": tour.get("operatorname"),
                    "flydate": tour.get("flydate"),
                    "nights": tour.get("nights"),
                    "price": tour.get("price"),
                    "fuelcharge": tour.get("fuelcharge"),
                    "priceue": tour.get("priceue"),
                    "placement": tour.get("placement"),
                    "adults": tour.get("adults"),
                    "child": tour.get("child"),
                    "meal": tour.get("meal"),
                    "mealrussian": tour.get("mealrussian"),
                    "room": tour.get("room"),
                    "tourname": tour.get("tourname"),
                    "currency": tour.get("currency"),
                    "regular": tour.get("regular"),
                    "promo": tour.get("promo"),
                    "onrequest": tour.get("onrequest"),
                    "flightstatus": tour.get("flightstatus"),
                    "hotelstatus": tour.get("hotelstatus"),
                    "nightflight": tour.get("nightflight")
                }
                flat_tours.append(flat_tour)
        
        # Сортируем по цене (от дешевых к дорогим)
        flat_tours.sort(key=lambda x: float(x.get("price", 999999)))
        
        # Возвращаем только ТОП-N туров
        return flat_tours[:limit] if limit else flat_tours
    
    async def search_tours(self, params: Dict) -> Dict:
        """Поиск туров (асинхронный) - ждём строго 3 секунды"""
        # Конвертируем параметры
        clean_params = self._convert_params(params)
        
        # Шаг 1: Создаем запрос
        search_response = await self._make_request("search.php", clean_params)
        
        # Проверяем на ошибки
        if search_response.get("iserror"):
            return search_response
        
        # API возвращает {"result": {"requestid": "..."}}
        request_id = search_response.get("result", {}).get("requestid")
        
        if not request_id:
            return {
                "iserror": True,
                "errormessage": "Не получен ID запроса",
                "api_response": search_response,
                "sent_params": clean_params
            }
        
        # Шаг 2: Ждём СТРОГО 3 секунды (без циклов)
        await asyncio.sleep(3)
        
        # Шаг 3: Получаем результаты (то что нашлось за 3 сек)
        result_params = {
            "requestid": request_id,
            "type": "result",
            "page": 1,
            "onpage": 25
        }
        return await self._make_request("result.php", result_params)
    
    async def search_tours_smart(self, city_name: str, country_name: str, params: Dict, limit: int = 10) -> Dict:
        """Умный поиск: находит коды города и страны, затем ищет туры
        
        Args:
            city_name: название города на русском
            country_name: название страны на русском
            params: дополнительные параметры поиска
            limit: максимальное количество туров в выдаче (по умолчанию 10)
        
        Returns:
            Словарь с результатами поиска
        """
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
        
        # Проверяем на ошибку
        if tours_result.get("iserror"):
            return {
                "success": False,
                "error": "search_failed",
                "city": city_result["city"],
                "country": country_result["country"],
                "search_params": search_params,
                "error_details": tours_result
            }
        
        # Шаг 5: Разворачиваем туры из отелей в плоский список (ТОП-N)
        flat_tours = self._flatten_tours(tours_result, limit=limit)
        
        # Шаг 6: Получаем статистику
        status = tours_result.get("data", {}).get("status", {})
        
        # Шаг 7: Возвращаем всё вместе
        return {
            "success": True,
            "city": city_result["city"],
            "country": country_result["country"],
            "search_params": search_params,
            "status": {
                "hotels_found": status.get("hotelsfound", 0),
                "tours_found": status.get("toursfound", 0),
                "tours_shown": len(flat_tours),
                "min_price": status.get("minprice", 0),
                "state": status.get("state", "unknown")
            },
            "tours": flat_tours,
            "hotels": tours_result
        }
    
    async def get_hot_tours_smart(self, city_name: str, countries: Optional[Any] = None, params: Dict = None) -> Dict:
        """Умный поиск горящих туров: находит коды города и стран
        
        Args:
            city_name: название города на русском
            countries: название страны, список стран или None для всех стран
            params: дополнительные параметры (items, maxdays, stars, etc)
        
        Returns:
            Словарь с горящими турами
        """
        if params is None:
            params = {}
        
        # Шаг 1: Находим город
        city_result = await self.find_city(city_name)
        if not city_result.get("found"):
            return {
                "success": False,
                "error": "city_not_found",
                "message": f"Город '{city_name}' не найден",
                "city_search": city_result
            }
        
        city_id = city_result["city"]["id"]
        
        # Шаг 2: Обрабатываем страны (если указаны)
        country_codes = None
        countries_info = None
        
        if countries:
            # Если строка - делаем список
            if isinstance(countries, str):
                countries_list = [c.strip() for c in countries.split(",")]
            elif isinstance(countries, list):
                countries_list = countries
            else:
                countries_list = [str(countries)]
            
            # Находим коды стран
            countries_result = await self.find_countries(countries_list)
            
            if not countries_result.get("found"):
                return {
                    "success": False,
                    "error": "countries_not_found",
                    "message": f"Страны не найдены: {countries}",
                    "countries_search": countries_result
                }
            
            countries_info = countries_result["countries"]
            country_codes = ",".join([str(c["id"]) for c in countries_info])
        
        # Шаг 3: Формируем параметры
        hot_params = {
            "city": city_id,
            "items": params.get("items", 10),  # По умолчанию 10
            **params
        }
        
        if country_codes:
            hot_params["countries"] = country_codes
        
        # Шаг 4: Получаем горящие туры
        hot_result = await self.get_hot_tours(hot_params)
        
        # Проверяем на ошибку
        if hot_result.get("iserror"):
            return {
                "success": False,
                "error": "api_error",
                "city": city_result["city"],
                "countries": countries_info,
                "hot_params": hot_params,
                "error_details": hot_result
            }
        
        # Шаг 5: Возвращаем результат
        return {
            "success": True,
            "city": city_result["city"],
            "countries": countries_info,
            "hot_params": hot_params,
            "hotcount": hot_result.get("hotcount", 0),
            "hottours": hot_result.get("hottours", [])
        }
    
    async def actualize_tour(self, tourid: str, currency: int = 0) -> Dict:
        """Актуализация тура (проверка цены)"""
        params = self._convert_params({
            "tourid": tourid,
            "currency": currency
        })
        result = await self._make_request("actualize.php", params)
        
        # Проверяем на ошибку
        if result.get("iserror"):
            return {
                **result,
                "tourid": tourid,
                "note": "Тур может быть устаревшим или недоступным"
            }
        
        return result
    
    async def get_tour_details(self, tourid: str, currency: int = 0) -> Dict:
        """Детальная актуализация (перелеты + доплаты)"""
        params = self._convert_params({
            "tourid": tourid,
            "currency": currency
        })
        result = await self._make_request("actdetail.php", params)
        
        # Проверяем на ошибку
        if result.get("iserror"):
            return {
                **result,
                "tourid": tourid,
                "note": "Не удалось получить детали. Тур может быть устаревшим или недоступным"
            }
        
        return result
    
    async def get_hotel_info(self, hotelcode: int, reviews: int = 0, imgbig: int = 1) -> Dict:
        """Информация об отеле"""
        params = self._convert_params({
            "hotelcode": hotelcode,
            "reviews": reviews,
            "imgbig": imgbig
        })
        result = await self._make_request("hotel.php", params)
        
        # Проверяем на ошибку
        if result.get("iserror"):
            return {
                **result,
                "hotelcode": hotelcode,
                "note": "Не удалось получить информацию об отеле"
            }
        
        return result
    
    async def get_hot_tours(self, params: Dict) -> Dict:
        """Горящие туры"""
        clean_params = self._convert_params(params)
        result = await self._make_request("hottours.php", clean_params)
        
        # Проверяем на ошибку
        if result.get("iserror"):
            return {
                **result,
                "note": "Не удалось получить горящие туры"
            }
        
        return result
