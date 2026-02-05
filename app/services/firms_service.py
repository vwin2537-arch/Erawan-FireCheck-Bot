import httpx
import csv
import logging
import io
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class FIRMSService:
    """
    NASA FIRMS API Integration
    Documentation: https://firms.modaps.eosdis.nasa.gov/api/area/
    """
    
    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
    
    SOURCES = [
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT"
    ]
    
    def __init__(self):
        self.map_key = settings.FIRMS_MAP_KEY
        self.area = f"{settings.AREA_WEST},{settings.AREA_SOUTH},{settings.AREA_EAST},{settings.AREA_NORTH}"
        
    async def get_hotspots(
        self,
        source: str = "VIIRS_SNPP_NRT",
        day_range: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Fetch hotspots from FIRMS API for a specific source
        """
        url = f"{self.BASE_URL}/{self.map_key}/{source}/{self.area}/{day_range}"
        
        logger.info(f"Fetching hotspots from FIRMS: {source} (range: {day_range})")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                content = response.text
                if not content or "invalid key" in content.lower():
                    logger.error(f"FIRMS API Error: {content}")
                    return []
                
                return self._parse_csv(content, source)
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error fetching FIRMS data: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching FIRMS data: {e}")
            return []

    async def get_all_sources(self, day_range: int = 2) -> List[Dict[str, Any]]:
        """
        Fetch from all VIIRS sources and combine
        """
        all_hotspots = []
        for source in self.SOURCES:
            hotspots = await self.get_hotspots(source, day_range)
            all_hotspots.extend(hotspots)
            
        logger.info(f"Combined {len(all_hotspots)} hotspots from all sources")
        return all_hotspots

    def _parse_csv(self, csv_data: str, source: str) -> List[Dict[str, Any]]:
        """
        Parse CSV response from FIRMS API
        """
        f = io.StringIO(csv_data)
        reader = csv.DictReader(f)
        
        hotspots = []
        for row in reader:
            try:
                # Basic cleaning and type conversion
                # Convert UTC to Thailand Time (UTC+7)
                utc_dt = datetime.strptime(f"{row['acq_date']} {row['acq_time']}", "%Y-%m-%d %H%M")
                th_dt = utc_dt + timedelta(hours=7)

                hotspot = {
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "brightness": float(row.get("brightness", 0)),
                    "scan": float(row.get("scan", 0)),
                    "track": float(row.get("track", 0)),
                    "acq_date": th_dt.strftime("%Y-%m-%d"),
                    "acq_time": th_dt.strftime("%H%M"),
                    "satellite": source.replace("_NRT", ""),
                    "instrument": row.get("instrument", ""),
                    "confidence": self._map_confidence(row.get("confidence", "")),
                    "version": row.get("version", ""),
                    "bright_t31": float(row.get("bright_t31", 0)),
                    "frp": float(row.get("frp", 0)),
                    "daynight": row.get("daynight", "D")
                }
                hotspots.append(hotspot)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing hotspot row: {e}")
                continue
                
        return hotspots

    def _map_confidence(self, conf: str) -> str:
        """Map confidence values to human readable strings"""
        if not conf:
            return "nominal"
        
        # VIIRS uses l, n, h
        if conf.lower() == 'h': return 'high'
        if conf.lower() == 'n': return 'nominal'
        if conf.lower() == 'l': return 'low'
        
        # MODIS uses 0-100
        try:
            val = int(conf)
            if val >= 80: return 'high'
            if val >= 30: return 'nominal'
            return 'low'
        except ValueError:
            return conf
