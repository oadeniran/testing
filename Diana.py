import os
import json
from datetime import datetime, date
import numpy as np
import pandas as pd
import asyncio
from natural_hazard_risk import NaturalHazardRiskAPI
from geospatial import SatelliteImagery
from macro_risk import MacroRiskInsights
from regulatory_risk import RegulatoryRiskAnalyzerLLM
from dotenv import load_dotenv

load_dotenv()

class Diana:
    def __init__(self, fema_url, wildfire_api_url, openai_api_key, project_name, country_code,
                 project_description, project_type, project_state, RegulatoryFilesUrls, project_goal,
                 fred_key=None, eia_key=None):
        
        self.api = NaturalHazardRiskAPI(
            fema_url=fema_url,
            wildfire_api_url=wildfire_api_url,
            openai_api_key=openai_api_key
        )
        self.satellite = SatelliteImagery()
        self.project_name = project_name
        self.country_code = country_code
        self.project_description = project_description
        self.project_state = project_state
        self.project_goal = project_goal
        self.project_type = project_type
        self.RegulatoryFilesUrls = RegulatoryFilesUrls
        self.api_keys = {
            'fred': fred_key,
            'eia': eia_key,
            'oai': openai_api_key
        }

    async def assess_macro_risks(self):
        macro_analysis = MacroRiskInsights(self.project_name, self.country_code, self.api_keys)
        await macro_analysis.run_analysis()
        return macro_analysis.summary

    def assess_natural_risks(self, latitude, longitude, start_date, end_date):
        flood_risk = self.api.assess_flood_risk(latitude, longitude)
        temp_risk = self.api.assess_extreme_temperature_risk(latitude, longitude, start_date, end_date)
        wildfire_risk = self.api.assess_wildfire_risk(latitude, longitude)
        print("HH", wildfire_risk)  
        return flood_risk, temp_risk, wildfire_risk
    
    def assess_regulatory_risks(self):
        regAnalyzer = RegulatoryRiskAnalyzerLLM(self.api_keys['oai'], project_name=self.project_name, project_goal=self.project_goal, project_description=self.project_description, 
                                                project_type=self.project_type, State=self.project_state, RegulatoryFilesUrls=self.RegulatoryFilesUrls)
        print("Loading Regulatory Documents...")
        regAnalyzer.load_documents()
        doc_summary, doc_analysis = regAnalyzer.analyze_documents()
        _, dsire_summary, dsire_analysis = regAnalyzer.analyze_dsire_data()
        report = regAnalyzer.generate_risk_report(doc_summary, doc_analysis, dsire_summary, dsire_analysis)
        return regAnalyzer.visualize_risk_assessment(report)

    def create_natural_risk_visualization(self, flood_risk, temp_risk, wildfire_risk):
        print("HH", wildfire_risk)
        return self.api.create_spider_plot(flood_risk, temp_risk, wildfire_risk)

    def generate_natural_risk_insight(self, flood_risk, temp_risk, wildfire_risk):
        return self.api.generate_insight(flood_risk, temp_risk, wildfire_risk)

    def generate_macro_risk_insight(self, macro_risk):
        # This method would need to be implemented, possibly using a language model
        return f"Macro risk analysis summary: {json.dumps(macro_risk, indent=2)}"

    def process_satellite_imagery(self, latitude, longitude):
        return self.satellite.process_and_analyze_image(latitude, longitude)

    def create_json_output(self, latitude, longitude, start_date, end_date, natural_risks, 
                           macro_risks, natural_insight, macro_insight, image_url, image_description, visualization_url,
                           regulatory_risks):
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "analysis_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "natural_risks": {"data": self.api.create_spider_plot_json(natural_risks['flood_risk'],
                                                           natural_risks['temperature_risk'], natural_risks['wildfire_risk']),
                            "insight":natural_insight
                        },
            "macro_risks": macro_risks,
            "satellite_imagery": {
                "image_url": image_url,
                "description": image_description
            },
            "regulatory_risks": {"data" : regulatory_risks,
                                 "Insight": "A chart showing the estimated Regulatory Risks"},
            "timestamp": datetime.now().isoformat()
        }


    async def run_analysis(self, latitude, longitude, start_date, end_date):
        analysis_res = None
        while type(analysis_res) != tuple:
            try:
                # Assess natural risks
                flood_risk, temp_risk, wildfire_risk = self.assess_natural_risks(latitude, longitude, start_date, end_date)
                natural_risks = {
                    "flood_risk": flood_risk,
                    "temperature_risk": temp_risk,
                    "wildfire_risk": wildfire_risk
                }

                # Assess regulatory risks
                regulatory_risks = self.assess_regulatory_risks()
                
                # Assess macro risks
                if type(natural_risks["wildfire_risk"]) != str:
                    macro_risks = await self.assess_macro_risks()
                
                    # Create natural risk visualization
                    visualization_url = self.create_natural_risk_visualization(flood_risk, temp_risk, wildfire_risk)
                    
                    # Generate insights
                    natural_insight = self.generate_natural_risk_insight(flood_risk, temp_risk, wildfire_risk)
                    macro_insight = self.generate_macro_risk_insight(macro_risks)
                    
                    # Process satellite imagery
                    _, image_url, image_description = self.process_satellite_imagery(latitude, longitude)
                    
                    # Create JSON output
                    analysis_res = "success", self.create_json_output(
                        latitude, longitude, start_date, end_date,
                        natural_risks, macro_risks,
                        natural_insight, macro_insight,
                        image_url, image_description, visualization_url,regulatory_risks
                    )
            except Exception as e:
                analysis_res = "error: "+str(e)
                print("Error:", e)
                
        return analysis_res[1]

def save_json_to_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# Usage example
if __name__ == "__main__":
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    
    diana = Diana(
        fema_url="https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query",
        wildfire_api_url="https://www.fire.ca.gov/umbraco/api/IncidentApi/List?inactive=false",
        openai_api_key=OPENAI_API_KEY,
        project_name="SolarStorage_Project1",
        country_code="USA",
        fred_key = os.environ.get('FRED_KEY'),
        eia_key = os.environ.get("EIA_KEY")
    )
    
    latitude, longitude = 37.3688, -122.0363  # Sunnyvale, CA coordinates
    start_date, end_date = "2010-08-20", "2024-08-20"
    
    async def run_diana():
        result = await diana.run_analysis(latitude, longitude, start_date, end_date)
        save_json_to_file(result, "diana_analysis_result.json")
        print("Analysis complete. Results saved to diana_analysis_result.json")

    asyncio.run(run_diana())