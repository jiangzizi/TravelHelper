import os
from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
SEARCHAPI_API_KEY = os.environ.get("SEARCHAPI_API_KEY", "28AyuF5WCrDYRi1msQcUhsAF") 
SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
mcp = FastMCP("hotelsearch")
async def make_searchapi_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """向searchapi.io发送请求并处理错误情况"""
    # 确保API Key被添加到参数中
    params["api_key"] = SEARCHAPI_API_KEY
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(SEARCHAPI_URL, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            error_detail = None
            try:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.json()
            except ValueError:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.text
            
            error_message = f"调用searchapi.io时出错: {e}"
            if error_detail:
                error_message += f", 详情: {error_detail}"
            
            return {"error": error_message}
        except Exception as e:
            return {"error": f"处理请求时发生未知错误: {e}"}


@mcp.tool()
async def search_google_hotels(
    q: str, 
    check_in_date: str, 
    check_out_date: str,
    gl: str = None,
    hl: str = None,
    currency: str = None,
    property_type: str = None,
    price_min: str = None,
    price_max: str = None,
    property_types: str = None,
    amenities: str = None,
    rating: str = None,
    free_cancellation: str = None,
    special_offers: str = None,
    for_displaced_individuals: str = None,
    eco_certified: str = None,
    hotel_class: str = None,
    brands: str = None,
    bedrooms: str = None,
    bathrooms: str = None,
    adults: str = None,
    children_ages: str = None,
    next_page_token: str = None
):
    """搜索Google酒店信息"""
    params = {
        "engine": "google_hotels",
        "q": q,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date
    }
    
    # 添加可选参数
    optional_params = {
        "gl": gl,
        "hl": hl,
        "currency": currency,
        "property_type": property_type,
        "price_min": price_min,
        "price_max": price_max,
        "property_types": property_types,
        "amenities": amenities,
        "rating": rating,
        "free_cancellation": free_cancellation,
        "special_offers": special_offers,
        "for_displaced_individuals": for_displaced_individuals,
        "eco_certified": eco_certified,
        "hotel_class": hotel_class,
        "brands": brands,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "adults": adults,
        "children_ages": children_ages,
        "next_page_token": next_page_token
    }
    
    # 添加有值的可选参数
    for key, value in optional_params.items():
        if value is not None:
            params[key] = value
    hotel_response = await make_searchapi_request(params)

    tool_result = {}
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("hotelsearch")
    logger.info(f"Received response: {len(hotel_response.get('properties', []))}")
    for idx, hotel in enumerate(hotel_response.get("properties", [])[:10]):
        logger.info(f"Processing hotel #{idx + 1}: {hotel.get('name')}")
        # logger.info(f"Hotel details: {hotel}")
        current_hotel = {}
        current_hotel["name"] = hotel.get("name")
        current_hotel["address"] = hotel.get("gps_coordinates", {})
        current_hotel["type"] = hotel.get("type")
        current_hotel["price_per_night"] = hotel.get("price_per_night")
        current_hotel["nearby_places"] = hotel.get("nearby_places", [])
        current_hotel["rating"] = hotel.get("rating")
        current_hotel["amenities"] = hotel.get("amenities", [])
        current_hotel["excluded_amenities"] = hotel.get("excluded_amenities", [])
        images = hotel.get("images", [])
        if images:
            current_hotel["main_image"] = images[0].get("original")
        else:
            current_hotel["main_image"] = None
        tool_result[idx] = current_hotel

    # logger.info(f"Processed {len(tool_result)} hotels successfully.")   
    return tool_result

if __name__ == "__main__":
    mcp.run(transport="stdio")