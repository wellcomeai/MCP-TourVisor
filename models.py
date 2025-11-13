from pydantic import BaseModel, Field
from typing import Optional, List

class SearchToursRequest(BaseModel):
    departure: int = Field(..., description="Код города вылета")
    country: int = Field(..., description="Код страны")
    datefrom: Optional[str] = Field(None, description="Дата от (ДД.ММ.ГГГГ)")
    dateto: Optional[str] = Field(None, description="Дата до (ДД.ММ.ГГГГ)")
    nightsfrom: Optional[int] = Field(7, description="Ночей от")
    nightsto: Optional[int] = Field(10, description="Ночей до")
    adults: Optional[int] = Field(2, description="Количество взрослых")
    child: Optional[int] = Field(0, description="Количество детей")
    childage1: Optional[int] = Field(None, description="Возраст ребенка 1")
    childage2: Optional[int] = Field(None, description="Возраст ребенка 2")
    childage3: Optional[int] = Field(None, description="Возраст ребенка 3")
    stars: Optional[int] = Field(None, description="Минимальная звездность")
    meal: Optional[int] = Field(None, description="Код типа питания")
    rating: Optional[int] = Field(None, description="Минимальный рейтинг")
    regions: Optional[str] = Field(None, description="Коды курортов через запятую")
    pricefrom: Optional[int] = Field(None, description="Цена от")
    priceto: Optional[int] = Field(None, description="Цена до")

class ActualizeTourRequest(BaseModel):
    tourid: str = Field(..., description="ID тура")
    currency: Optional[int] = Field(0, description="Валюта: 0=RUB, 1=USD/EUR")

class GetHotToursRequest(BaseModel):
    city: int = Field(..., description="Код города вылета")
    items: int = Field(10, description="Количество туров")
    city2: Optional[int] = Field(None, description="Дополнительный город")
    city3: Optional[int] = Field(None, description="Дополнительный город 3")
    maxdays: Optional[int] = Field(None, description="Максимум дней от сегодня")
    countries: Optional[str] = Field(None, description="Коды стран через запятую")
    stars: Optional[int] = Field(None, description="Минимальная звездность")

class GetHotelInfoRequest(BaseModel):
    hotelcode: int = Field(..., description="Код отеля")
    reviews: Optional[int] = Field(0, description="Включить отзывы: 0 или 1")
    imgbig: Optional[int] = Field(1, description="Большие фото: 0 или 1")
