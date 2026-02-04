from geopy.geocoders import Nominatim
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)

def get_location_info(lat: float, lon: float) -> Dict[str, str]:
    """
    Get province and district from coordinates.
    Since FIRMS data can be high volume, we should use this sparingly
    or use a local database/cache.
    """
    # This is a placeholder for a more robust local geocoding system
    # For now, it returns dummy data or could be extended with geopy
    return {
        "province": "เชียงใหม่", # Sample
        "district": "แม่แจ่ม"     # Sample
    }
