"""
Oil Trading Desk — AIS Tanker Feed

Subscribes to aisstream.io WebSocket to receive real-time AIS vessel tracking data.
Filters for tanker ship types (80-89) within 7 major petroleum anchorages.
Maintains a 90-minute stale purge for vessels that stop transmitting.
"""

import asyncio
import json
import logging
import time
import websockets

import config
from hub import hub

logger = logging.getLogger("otd.feeds.ais")

# 7 bounding boxes for major petroleum anchorages/terminals
# Format: [[MinLat, MinLon], [MaxLat, MaxLon]]
BOUNDING_BOXES = [
    # Houston / Galveston
    [[28.9, -95.5], [29.8, -94.5]],
    # LOOP (Louisiana Offshore Oil Port)
    [[28.7, -90.2], [29.0, -89.8]],
    # Rotterdam / ARA
    [[51.8, 3.8], [52.1, 4.3]],
    # Singapore / Malacca Strait
    [[1.1, 103.5], [1.4, 104.1]],
    # Fujairah UAE
    [[25.0, 56.3], [25.5, 56.5]],
    # Caribbean (Venezuela / Curacao)
    [[10.0, -71.5], [12.0, -69.0]],
    # Saldanha Bay (South Africa)
    [[-33.1, 17.9], [-32.9, 18.1]],
]

# Tanker Ship Types (AIS specification)
TANKER_TYPES = set(range(80, 90))

# 90 minutes in seconds
STALE_PURGE_SECONDS = 90 * 60


async def fetch_ais_stream():
    """
    Long-lived WebSocket connection to aisstream.io.
    Updates hub.tankers directly.
    """
    if not config.HAS_AIS_KEY:
        hub.update_feed_status("ais", False, error="No API key", synthetic=True)
        # Populate some synthetic tanker data for demonstration if no key
        hub.tankers = _get_synthetic_tankers()
        return

    url = "wss://stream.aisstream.io/v0/stream"
    
    subscription_msg = {
        "APIKey": config.AIS_API_KEY,
        "BoundingBoxes": BOUNDING_BOXES,
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
    }

    while True:
        try:
            hub.update_feed_status("ais", True)
            
            async with websockets.connect(url, max_size=None) as ws:
                await ws.send(json.dumps(subscription_msg))
                logger.info("Connected to aisstream.io WebSocket")
                
                async for message in ws:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("MessageType")
                        meta = data.get("MetaData", {})
                        
                        mmsi = meta.get("MMSI", 0)
                        if not mmsi:
                            continue
                            
                        # Only keep tankers if type is known
                        ship_type = meta.get("ShipType", 0)
                        
                        # Initialize vessel if new
                        if mmsi not in hub.tankers:
                            hub.tankers[mmsi] = {
                                "mmsi": mmsi,
                                "name": meta.get("ShipName", f"Unknown-{mmsi}"),
                                "type": ship_type,
                                "lat": meta.get("latitude", 0),
                                "lon": meta.get("longitude", 0),
                                "destination": "",
                                "last_seen": time.time(),
                            }
                            
                        vessel = hub.tankers[mmsi]
                        vessel["last_seen"] = time.time()
                        
                        if msg_type == "PositionReport":
                            msg = data.get("Message", {}).get("PositionReport", {})
                            if msg:
                                vessel["lat"] = msg.get("Latitude", vessel["lat"])
                                vessel["lon"] = msg.get("Longitude", vessel["lon"])
                                
                        elif msg_type == "ShipStaticData":
                            msg = data.get("Message", {}).get("ShipStaticData", {})
                            if msg:
                                new_type = msg.get("Type", 0)
                                if new_type:
                                    vessel["type"] = new_type
                                vessel["name"] = msg.get("Name", vessel["name"]).strip()
                                vessel["destination"] = msg.get("Destination", vessel["destination"]).strip()

                        # Purge non-tankers if we just learned their type
                        if vessel["type"] > 0 and vessel["type"] not in TANKER_TYPES:
                            del hub.tankers[mmsi]
                            
                    except json.JSONDecodeError:
                        continue
                    
                    # Periodic cleanup
                    if time.time() % 60 < 1:  # check roughly every minute
                        _purge_stale_vessels()

        except websockets.ConnectionClosed:
            logger.warning("aisstream.io WebSocket closed, reconnecting in 5s...")
            hub.update_feed_status("ais", False, error="Connection closed")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"aisstream.io WebSocket error: {e}")
            hub.update_feed_status("ais", False, error=str(e))
            await asyncio.sleep(5)


def _purge_stale_vessels():
    """Remove vessels that haven't sent a message in 90 minutes."""
    now = time.time()
    stale_mmsis = [
        mmsi for mmsi, v in hub.tankers.items() 
        if (now - v["last_seen"]) > STALE_PURGE_SECONDS
    ]
    for mmsi in stale_mmsis:
        del hub.tankers[mmsi]


def _get_synthetic_tankers():
    """Return synthetic tanker data for when API key is missing."""
    now = time.time()
    return {
        123456789: {"mmsi": 123456789, "name": "SYNTHETIC TANKER 1", "type": 80, "lat": 29.5, "lon": -95.0, "destination": "HOUSTON", "last_seen": now},
        987654321: {"mmsi": 987654321, "name": "SYNTHETIC TANKER 2", "type": 84, "lat": 51.9, "lon": 4.0, "destination": "ROTTERDAM", "last_seen": now},
        111222333: {"mmsi": 111222333, "name": "SYNTHETIC TANKER 3", "type": 80, "lat": 1.25, "lon": 103.8, "destination": "SINGAPORE", "last_seen": now},
    }
