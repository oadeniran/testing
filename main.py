import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from Diana import Diana, save_json_to_file # Import the Diana class and the save_json_to_file function
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from utils import save_analysis_to_db
from onboarding_chat import onboarding_chat, get_chat_history
import requests

load_dotenv()

# Load Environment Variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FRED_KEY = os.environ.get("FRED_KEY")
EIA_KEY = os.environ.get("EIA_KEY")
DERVET_URL = os.environ.get("DERVET_URL")

# Define the FastAPI app
prefix = "/diana"
title = "Diana Project Analysis API"
description = "An API for analyzing project risks and generating insights"
tags_metadata = [
    {
        "name": "Diana",
        "description": "Operations related to Diana project analysis",
    },
]
app = FastAPI(
    docs_url=prefix + "/dev/documentation",
    openapi_url=prefix + "/openapi.json",
    title=title,
    description=description,
    openapi_tags=tags_metadata,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str = "Wagwaan my G"
    project_id:str = "652f3b8e9f1b8b2a6c8b4567"

class ProjectDescription(BaseModel):
    project_id: str = "project_id"
    project_name: str = "SolarStorage_Project1"
    project_type: str = "Solar and Storage"
    country_code: str = "USA"
    location: str = "California"
    estimated_project_duration:str = "10 years",
    latitude: float = 37.3688
    longitude: float = -122.0363
    description: str = "This is a test project for analyzing the Diana API."
    start_date: str = "2010-08-20"
    end_date: str = "2024-08-20"
    project_goal: str = "Project Goal"
    tarrif_data: list = ["https://exoaidev.blob.core.windows.net/files/25147b50-7918-11ef-9a10-b37edabff1cd-1727033008005-DER-VET_User_Guide_v0.1.1.pdf"]
    load_shape_data: list = ["https://exoaidev.blob.core.windows.net/files/25147b50-7918-11ef-9a10-b37edabff1cd-1727033008005-DER-VET_User_Guide_v0.1.1.pdf"]
    regulatory_data: list = ["https://exoaidev.blob.core.windows.net/files/25147b50-7918-11ef-9a10-b37edabff1cd-1727033008005-DER-VET_User_Guide_v0.1.1.pdf"]


@app.get(f"{prefix}/", summary="Root endpoint", response_description="Welcome message")
async def root():
    return {"message": "Welcome to the Diana Project Analysis API"}

@app.post("/analyze_project", summary="Analyze a project", response_description="Comprehensive project analysis")
async def analyze_project(project: ProjectDescription):
    result = {}
    try:
        diana = Diana(
            fema_url="https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query",
            wildfire_api_url="https://www.fire.ca.gov/umbraco/api/IncidentApi/List?inactive=false",
            openai_api_key=OPENAI_API_KEY,
            project_name=project.project_name,
            country_code=project.country_code,
            fred_key=FRED_KEY,
            eia_key=EIA_KEY,
            project_description = project.description, 
            project_state = project.location, 
            RegulatoryFilesUrls = project.regulatory_data,
            project_goal=project.project_goal
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        analysis_result = await diana.run_analysis(project.latitude, project.longitude, project.start_date, project.end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if analysis_result is not None:
            result["project_id"] = project.project_id
            result["project_name"] = project.project_name
            result["project_type"] = project.project_type
            result["project_description"] = project.description
            result["project_goal"] = project.project_goal
            result["country_code"] = project.country_code
            result["Analysis"] = analysis_result
            save_analysis_to_db(result)
            ## Get DERVET data
            try:
                response = requests.post(DERVET_URL,
                                         json = {
                                            "load_shape_data": project.load_shape_data,
                                            "tarrif_data" : project.tarrif_data,
                                            "start_date" : project.start_date,
                                            "longitude" : project.longitude,
                                            "latitude": project.latitude,
                                            "project_id": project.project_id
                                         })
                if response.status_code == 200:
                    dervet_data = response.json()
            except Exception as e:
                print("Error fetching DERVET data:", e)
                raise HTTPException(status_code=500, detail="Error fetching DERVET data:" + str(e))
            # save_json_to_file(result, "diana_analysis_result.json")
            print("Analysis complete. Results saved to diana_analysis_result.json")
            result["_id"] = str(result["_id"])
            return {
                "Result" : "Success",
                "Msg" : "All analysis fully completed",
                "analysis_obj_id" : result["_id"],
                "project_id" : result["project_id"]}

@app.get(f"/chat-history", summary="Chat history", response_description="Chat history")
async def chat_history(project_id:str = "652f3b8e9f1b8b2a6c8b4567"):
    try:
        response = get_chat_history(project_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@app.post("/chat-onboarding", summary="Chat onboarding", response_description="Chat onboarding")
async def chat_onboarding(message: Message):
    try:
        response =  onboarding_chat(message.project_id, message.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)