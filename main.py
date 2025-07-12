from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
import json
import os
import httpx
from typing import AsyncGenerator

from models.ItineraryModels import Itinerary, ItineraryItem
from models.ActivityModels import CategoryList
from utils.activity_formatter import format_activity

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      
    allow_credentials=False,  
    allow_methods=["*"],      
    allow_headers=["*"], 
)

@app.get("/health")
def sendHello():
    return "Server healthy"

@app.get("/sample-response")
def getSampleResponse():
    model = ChatOpenAI(model="gpt-4.1")
    structured_output_model = model.with_structured_output(Itinerary)

    system_prompt = SystemMessage(content="""
    You are a travel planning assistant that creates personalized trip itineraries based on a set of activities provided by the user.

    Each activity includes:
    - An activity name
    - A description (to help you understand the type and nature of the activity)
    - Location information (latitude and longitude coordinates)
    - An estimated duration in hours or minutes

    You should:
    - Estimate travel time between activities using the Haversine distance formula
    - Decide the optimal sequence of activities based on their descriptions, duration, and travel time
    - Insert appropriate rest intervals based on the flow of the itinerary (e.g., after physically demanding activities or during long gaps)
    - Mark any unused time slots as "rest"

    Guidelines:
    - The itinerary should ideally begin at **8:00 AM** and conclude by **11:59 PM**, but this is flexible depending on the nature of the activities
    - For example: trekking may require an early morning start, and club visits may happen late at night
    - The output should be a continuous, well-structured itinerary covering the full day and they may span multiple days based on the activities provided or if you feels it will become overwhelming for the user

    Always ensure the itinerary feels balanced, practical, and enjoyable for the traveler.
    """)

    messages = [system_prompt]
    messages.append(HumanMessage("""
    The trip begins on 17th June,2025
        Here is the list of activities selected by the user:
        1. Activity Name: Sunrise Trek to Tiger Hill  
        Description: A physically demanding early morning trek to Tiger Hill to view the sunrise over the mountains.  
        Location: Latitude 27.0348, Longitude 88.2636  
        Estimated Duration: 2 hours

        2. Activity Name: Visit to Batasia Loop  
        Description: A scenic spot where the toy train makes a loop, with gardens and views of the Himalayas.  
        Location: Latitude 27.0174, Longitude 88.2512  
        Estimated Duration: 1 hour

        3. Activity Name: Breakfast at Keventers  
        Description: Light breakfast at the iconic Keventers cafe with panoramic views.  
        Location: Latitude 27.0418, Longitude 88.2656  
        Estimated Duration: 45 minutes

        4. Activity Name: Tea Garden Walk  
        Description: A relaxed walk through the Happy Valley Tea Estate with opportunities to learn about tea production.  
        Location: Latitude 27.0574, Longitude 88.2672  
        Estimated Duration: 1.5 hours

        5. Activity Name: Lunch at Glenary's  
        Description: Popular bakery and restaurant offering continental and local cuisine.  
        Location: Latitude 27.0415, Longitude 88.2648  
        Estimated Duration: 1 hour

        6. Activity Name: Visit to Peace Pagoda  
        Description: A serene Buddhist pagoda offering panoramic views of the town and mountains.  
        Location: Latitude 27.0577, Longitude 88.2646  
        Estimated Duration: 1 hour

        7. Activity Name: Dinner at Shangri-La  
        Description: Fine dining restaurant with Himalayan cuisine, perfect for a relaxing end to the day.  
        Location: Latitude 27.0413, Longitude 88.2627  
        Estimated Duration: 1.5 hours

        8. Activity Name: Explore Local Club Night  
        Description: Experience Darjeeling's nightlife at a popular local club with music and drinks.  
        Location: Latitude 27.0420, Longitude 88.2631  
        Estimated Duration: 2 hours
    """))
    
    res = structured_output_model.invoke(messages)
    return {"itinerary": res}

class DescriptionBody(BaseModel):
    description:str
@app.post("/get-recommendations")
async def getItinerary(descriptionBody:DescriptionBody):
    try:
        model=ChatOpenAI(model="gpt-4.1",temperature=0.1)
        messages=[] 
        system_message = SystemMessage(content="""
        You are a helpful assistant that receives user descriptions about their desired trip experience.
        Your task is to analyze these descriptions and infer the types of activity categories the user is most likely interested in.
        You are allowed to infer loosely, and try to associate as many categories as you can.
        """)
        human_message=HumanMessage(content=descriptionBody.description)

        structured_model=model.with_structured_output(schema=CategoryList)

        messages.extend([system_message,human_message])
        result=structured_model.invoke(messages)
        print(result)
        return {
            "category_list":result.category_list
        }
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# Alternative approach using Server-Sent Events (SSE)
@app.get("/stream-itinerary-sse/{userId}")
async def stream_itinerary_sse(userId :str):
    async def generate_sse_stream(userId) -> AsyncGenerator[str, None]:
        try:
            activity_list=[]
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{os.getenv('SPRING_API_URL')}/activities?userId={userId}")
                if response.status_code == 200:
                    data=response.json()
                    print(data)
                    activity_list=data["data"]
                    if(len(activity_list)==0):
                        raise Exception ("No activities selected")
                else:
                    raise Exception ("Internal server error, unable to relay data to LLM")

            # Send initial connection message
            yield "data: " + json.dumps({"type": "connected", "message": "Stream started"}) + "\n\n"
            
            model = ChatOpenAI(
                model="gpt-4.1",
                streaming=True,
                temperature=0.1
            )

            system_prompt = SystemMessage(content="""
            You are a travel planning assistant. Create an itinerary from a selected list of activities and present each activity as a separate JSON object.
                                          
            Each activity includes:
            - An activity name
            - A description (to help you understand the type and nature of the activity)
            - Location information (latitude and longitude coordinates)
            - An estimated duration in hours or minutes

            You should:
            - Estimate travel time between activities using the Haversine distance formula
            - Decide the optimal sequence of activities based on their descriptions, duration, and location.
            - Insert appropriate rest intervals based on the flow of the itinerary (e.g., after physically demanding activities or during long gaps)
            - Mark any unused time slots as "rest"
            - Keep roughly 4-5 activities per day and move on to the following day, unless you think it's necessary to include more.

            Guidelines:
            - A day should ideally begin at **8:00 AM** and conclude by **11:59 PM**, but this is flexible depending on the nature of the activities
            - For example: trekking may require an early morning start, and club visits may happen late at night
            - The output should be a continuous, well-structured itinerary covering the full day and they may span multiple days based on the activities provided or if you feels it will become overwhelming for the user

            Always ensure the itinerary feels balanced, practical, and enjoyable for the traveler.
            
            For each activity, output exactly this format:
            {"activity_name": "...", "activity_type": "...", "start_time": "...", "end_time": "...", "activity_id":"..."}
            
            Output one activity per line, followed by a newline.
            Activity types must be one of: "rest", "adventure", "tourist attraction", "commute"
            Times must be in ISO 8601 format: "2025-06-27T08:00:00"
            For activities of type 'rest' or 'commute' as well as activities not linked to the activity list, set a randomly generate activity id, otherwise use the given activity_id
            
            Start the itinerary at 8:00 AM on July 15th, 2025, you may span it across several days
            """)

            formatted_activity_message=format_activity(activity_list)


            messages = [system_prompt]
            messages.append(HumanMessage(f"""
            Create an itinerary for these activities in Delhi:
            {formatted_activity_message}
            """))

            # Stream and parse response
            full_response = ""
            async for chunk in model.astream(messages):
                if chunk.content:
                    full_response += chunk.content
                    
                    # Look for complete JSON lines
                    lines = full_response.split('\n')
                    for i, line in enumerate(lines[:-1]):  # Exclude the last incomplete line
                        line = line.strip()
                        if line and line.startswith('{') and line.endswith('}'):
                            try:
                                item_data = json.loads(line)
                                if all(key in item_data for key in ['activity_name', 'activity_type', 'start_time', 'end_time','activity_id']):
                                    yield f"data: {json.dumps({'type': 'item', 'data': item_data})}\n\n"
                                    # Remove processed line from full_response
                                    full_response = '\n'.join(lines[i+1:])
                                    break
                            except json.JSONDecodeError:
                                continue
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
        except Exception as e:
            print(e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_sse_stream(userId),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


# Streaming endpoint
# @app.get("/stream-itinerary")
# async def stream_itinerary():
#     async def generate_itinerary_stream() -> AsyncGenerator[str, None]:
#         try:
#             # Initialize the model for streaming
#             model = ChatOpenAI(
#                 model="gpt-4.1",
#                 streaming=True,
#                 temperature=0
#             )
            
#             # Modified system prompt to encourage JSON streaming
#             system_prompt = SystemMessage(content="""
#             You are a travel planning assistant that creates personalized trip itineraries based on a set of activities provided by the user.

#             Each activity includes:
#             - An activity name
#             - A description (to help you understand the type and nature of the activity)
#             - Location information (latitude and longitude coordinates)
#             - An estimated duration in hours or minutes

#             You should:
#             - Estimate travel time between activities using the Haversine distance formula
#             - Decide the optimal sequence of activities based on their descriptions, duration, and travel time
#             - Insert appropriate rest intervals based on the flow of the itinerary (e.g., after physically demanding activities or during long gaps)
#             - Mark any unused time slots as "rest"

#             Guidelines:
#             - The itinerary should ideally begin at **8:00 AM** and conclude by **11:59 PM**, but this is flexible depending on the nature of the activities
#             - For example: trekking may require an early morning start, and club visits may happen late at night
#             - The output should be a continuous, well-structured itinerary covering the full day and they may span multiple days based on the activities provided or if you feels it will become overwhelming for the user

#             Always ensure the itinerary feels balanced, practical, and enjoyable for the traveler.

#             IMPORTANT: Respond with a valid JSON object containing an "items" array. Each item should have:
#             - activity_name: string
#             - activity_type: one of ["rest", "adventure", "tourist attraction", "commute"]
#             - start_time: ISO 8601 datetime string
#             - end_time: ISO 8601 datetime string

#             Format your response as a single JSON object with the structure:
#             {
#                 "items": [
#                     {
#                         "activity_name": "...",
#                         "activity_type": "...",
#                         "start_time": "2025-06-27T08:00:00",
#                         "end_time": "2025-06-27T10:00:00"
#                     }
#                 ]
#             }
#             """)

#             messages = [system_prompt]
#             messages.append(HumanMessage("""
#             The trip begins on 27th June,2025
#                 Here is the list of activities selected by the user:
#                 1. Activity Name: Sunrise Trek to Tiger Hill  
#                 Description: A physically demanding early morning trek to Tiger Hill to view the sunrise over the mountains.  
#                 Location: Latitude 27.0348, Longitude 88.2636  
#                 Estimated Duration: 2 hours

#                 2. Activity Name: Visit to Batasia Loop  
#                 Description: A scenic spot where the toy train makes a loop, with gardens and views of the Himalayas.  
#                 Location: Latitude 27.0174, Longitude 88.2512  
#                 Estimated Duration: 1 hour

#                 3. Activity Name: Breakfast at Keventers  
#                 Description: Light breakfast at the iconic Keventers cafe with panoramic views.  
#                 Location: Latitude 27.0418, Longitude 88.2656  
#                 Estimated Duration: 45 minutes

#                 4. Activity Name: Tea Garden Walk  
#                 Description: A relaxed walk through the Happy Valley Tea Estate with opportunities to learn about tea production.  
#                 Location: Latitude 27.0574, Longitude 88.2672  
#                 Estimated Duration: 1.5 hours

#                 5. Activity Name: Lunch at Glenary's  
#                 Description: Popular bakery and restaurant offering continental and local cuisine.  
#                 Location: Latitude 27.0415, Longitude 88.2648  
#                 Estimated Duration: 1 hour

#                 6. Activity Name: Visit to Peace Pagoda  
#                 Description: A serene Buddhist pagoda offering panoramic views of the town and mountains.  
#                 Location: Latitude 27.0577, Longitude 88.2646  
#                 Estimated Duration: 1 hour

#                 7. Activity Name: Dinner at Shangri-La  
#                 Description: Fine dining restaurant with Himalayan cuisine, perfect for a relaxing end to the day.  
#                 Location: Latitude 27.0413, Longitude 88.2627  
#                 Estimated Duration: 1.5 hours

#                 8. Activity Name: Explore Local Club Night  
#                 Description: Experience Darjeeling's nightlife at a popular local club with music and drinks.  
#                 Location: Latitude 27.0420, Longitude 88.2631  
#                 Estimated Duration: 2 hours
#             """))

#             # Stream the response
#             full_response = ""
#             async for chunk in model.astream(messages):
#                 if chunk.content:
#                     full_response += chunk.content
                    
#                     # Try to parse partial JSON and extract complete items
#                     try:
#                         # Look for complete JSON objects in the response
#                         if '"items"' in full_response and ']' in full_response:
#                             # Try to parse the JSON
#                             start_idx = full_response.find('{')
#                             if start_idx != -1:
#                                 json_part = full_response[start_idx:]
#                                 try:
#                                     parsed = json.loads(json_part)
#                                     if 'items' in parsed:
#                                         # Send each item as it becomes available
#                                         for item in parsed['items']:
#                                             yield f"data: {json.dumps({'type': 'item', 'data': item})}\n\n"
#                                         break
#                                 except json.JSONDecodeError:
#                                     # Continue accumulating if JSON is incomplete
#                                     continue
#                     except Exception:
#                         continue
            
#             # Send completion signal
#             yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
#         except Exception as e:
#             yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

#     return StreamingResponse(
#         generate_itinerary_stream(),
#         media_type="text/plain",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "Access-Control-Allow-Origin": "*",
#             "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
#             "Access-Control-Allow-Headers": "*",
#         }
#     )