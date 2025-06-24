from pydantic import BaseModel, Field
from typing import Literal,List
from datetime import datetime

class ItineraryItem(BaseModel):
    """
    Represents a single item in a travel itinerary, specifying the activity, type, and its time window.
    """

    activity_name: str = Field(
        description="Name of the activity the tourist will engage in during the specified time."
    )

    activity_type: Literal["rest", "adventure", "tourist attraction", "commute"] = Field(
        description=(
            "Category of the activity:\n"
            "- 'rest' for breaks, meals, or idle time\n"
            "- 'adventure' for physically engaging experiences like trekking or bungee jumping\n"
            "- 'tourist attraction' for visiting landmarks, monuments, or cultural sites\n"
            "- 'commute' for travel between locations via any mode (cab, train, bus, etc.)"
        )
    )

    start_time: datetime = Field(
        description="Start time of the activity in ISO 8601 format (e.g., '2025-06-15T08:00:00')."
    )

    end_time: datetime = Field(
        description="End time of the activity in ISO 8601 format (e.g., '2025-06-15T09:30:00')."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "activity_name": "Visit the Eiffel Tower",
                "activity_type": "tourist attraction",
                "start_time": "2025-06-15T09:00:00",
                "end_time": "2025-06-15T11:00:00"
            }
        }

class Itinerary(BaseModel):
    items: List[ItineraryItem]

