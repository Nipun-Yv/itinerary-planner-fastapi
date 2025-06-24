from pydantic import BaseModel,Field
from typing import Literal,List

class CategoryType(BaseModel):
    category_type:Literal['Fitness', 'Sensory', 'Food & Drink', 'Art', 'History', 'Accommodation', 'Spiritual', 'Retail Therapy', 'Water Sports', 'Local Experience', 'Patriotic', 'Relaxation', 'Educational', 'Recreational', 'Sightseeing', 'Food & Culture', 'Nature', 'Adventure', 'Wellness', 'Cultural', 'Leisure', 'Heritage']=Field(
        description="An activity category that is assumed and inferred from user description"
    )
    
class CategoryList(BaseModel):
    category_list:List[CategoryType]=Field(description="A list of categories that is further used to filter and search activities by category for the user")